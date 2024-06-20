# import time
import asyncio
from contextlib import asynccontextmanager
import sys

import time
import traceback

from fastapi import FastAPI, Request
from pynput import keyboard
from uvicorn import Config, Server

from colorama import Fore, Style
from core import LOG, event
from core.util.accumulator import Accumulator
from core.util.beeps import beep, beeper
from core.util.console_utils import print_markdown
from core.util.process_utils import create_daemon

from core.util.spotify import play_playback, pause_playback
from intercept_notification import start_notification_observer
from kernel import put_kernel_messages_into_queue
from profiles.mac_os import interpreter

accumulator = Accumulator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    LOG.info("Starting assistant program...")
    beep("Blow")
    stream.feed("At your service sir.")
    stream.play()
    print("")
    print_markdown("○")
    print_markdown("\n*Ready...*\n")
    print(f"\nPress and hold {wake_key}, speak, then release.\n")
    yield
    LOG.info("Shutting down audio recorder...")
    # recorder.shutdown()
    stream.feed("Shutting down now sir")
    stream.play_async()
    print_markdown("*Server is shutting down*")
    LOG.info("Shutting down assistant...")


# Server
app = FastAPI(lifespan=lifespan)

# Queue
from_user = asyncio.Queue()
from_computer = asyncio.Queue()

HOST = "0.0.0.0"
PORT = 8008

wake_key = keyboard.Key.f8

# Button state
is_pressed = False
last_pressed = 0
playback_paused = False


@app.post("/")
async def add_computer_message(request: Request):
    body = await request.json()
    text = body.get("text")
    if not text:
        return {"error": "Missing 'text' in request body"}, 422
    message = {
        "role": "computer",
        "format": "output",
        "type": "console",
        "content": text,
    }
    await from_computer.put({"role": "computer", "type": "console", "start": True})
    await from_computer.put(message)
    await from_computer.put({"role": "computer", "type": "console", "end": True})


# @app.post("/speak")
# async def speak(request: Request):
#     body = await request.json()
#     text = body.get("text")
#     if not text:
#         return {"error": "Missing 'text' in request body"}, 422
#     LOG.info(f"Speak: {text}")
#     stream.feed(text)
#     stream.play()


def connect_events(event):
    event.on("stream.stop", stop_speech)


def process_text(utterance):
    if isinstance(utterance, str):
        print(f"> {Fore.YELLOW + utterance + Style.RESET_ALL}\n")

    try:
        stream.feed(generator(utterance))
        stream.play_async()
    except Exception:
        sys.exit(1)
        # return


def stop_speech():
    stream.stop()


def generator(utterance):
    global last_pressed

    if time.time() - last_pressed > 0.25:
        try:
            old_last_pressed = last_pressed
            for chunk in interpreter.chat(utterance, display=True, stream=True):
                # Halt current execution to process new speech utterance
                if old_last_pressed != last_pressed:
                    beeper.stop()
                    LOG.warning("Not running due to premature keypress")
                    break

                content = chunk.get("content")

                if chunk.get("type") == "message":
                    if content:
                        beeper.stop()

                        # Experimental: The AI voice sounds better with replacements like these, but it should happen at the TTS layer
                        content = (
                            content.replace(". ", ". ... ")
                            .replace(",", "")
                            .replace(", sir.", " sir...")
                            .replace(", sir", " sir...")
                            .replace("!", "! ... ")
                            .replace("?", "? ... ")
                        )
                        LOG.debug(f"Speak: {content}")

                        yield content

                elif chunk.get("type") == "code":
                    if "start" in chunk:
                        beeper.start()

                    # Experimental: If the AI wants to type, we should type immediatly
                    # if (
                    #     interpreter.messages[-1]
                    #     .get("content")
                    #     .startswith("computer.keyboard.write(")
                    # ):
                    #     controller.type(content)
        # except KeyboardInterrupt:
        #     raise
        except Exception:
            LOG.exception(traceback.format_exc())
            return


def on_press(key):
    global is_pressed, last_pressed, playback_paused
    if key == wake_key and not is_pressed:
        beep("Morse")
        pause_playback()
        playback_paused = True
        is_pressed = True
        last_pressed = time.time()
        recorder.start()
        stream.stop()


def on_release(key):
    global is_pressed

    if key == wake_key and is_pressed:
        recorder.stop()
        is_pressed = False


def on_speaking_end():
    global playback_paused
    if playback_paused:
        play_playback()
        playback_paused = False


def push_to_talk_listener():
    LOG.info("Starting push to talk listener...")
    try:
        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()
    except Exception as e:
        LOG.exception(f"Error in start_keyboard_listener: {e}")


def speech_listener(recorder):
    LOG.info("Starting speech listener...")
    while True:
        recorder.text(process_text)
        time.sleep(2)


# TODO: refactor name this isn't a websocket listener
async def websocket_listener():
    LOG.info("Starting websocket listener...")
    while True:
        if not from_user.empty():
            LOG.info("Message gotten from user...")
            chunk = await from_user.get()
            # LOG.info(f"Message from user: {chunk}")
        elif not from_computer.empty():
            chunk = await from_computer.get()
            # LOG.info(f"Message from computer: {chunk}")
        else:
            await asyncio.sleep(1)
            continue

        message = accumulator.accumulate(chunk)

        if message is None:
            continue

        if not isinstance(message["content"], str):
            print("This should be a string, but it's not:", message["content"])
            message["content"] = message["content"].decode()

        LOG.info(f"message from websocket: {message}")
        process_text(message)


async def main():
    start_notification_observer()
    push_to_talk_listener()
    asyncio.create_task(websocket_listener())
    asyncio.create_task(put_kernel_messages_into_queue(from_computer))
    create_daemon(target=speech_listener, args=(recorder,))
    connect_events(event)

    config = Config(app=app, host=HOST, port=PORT, log_level="critical")
    server = Server(config)
    await server.serve()


if __name__ == "__main__":
    from core.stt import recorder_config, AudioToTextRecorder
    from core.tts import engine, TextToAudioStream

    recorder = AudioToTextRecorder(**recorder_config)
    stream = TextToAudioStream(engine=engine, on_audio_stream_stop=on_speaking_end)

    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    asyncio.run(main())
