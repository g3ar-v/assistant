# import time
import asyncio
import traceback
from contextlib import asynccontextmanager
import sys
import time


from fastapi import FastAPI, Request
from pynput import keyboard
from uvicorn import Config, Server

from colorama import Fore, Style
from clock import clock
from core.util.log import LOG
from core.util.accumulator import Accumulator
from core.util.beeps import beep
from core.util.console_utils import print_markdown
from core.util.process_utils import create_daemon
from core.util.spotify import pause_playback

from intercept_notification import start_notification_observer
from kernel import put_kernel_messages_into_queue

from core.stt.stt import STT
from core.tts.tts import TTS
from core.util.beeps import beeper
from profiles.mac_os import interpreter

from async_interpreter import generator
from pyee import EventEmitter


# from core.stt.audio_recorder import AudioToTextRecorder
# from RealtimeSTT import AudioToTextRecorder

event = EventEmitter()

accumulator = Accumulator()


stream = None


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
recorder = None


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
    if utterance:
        if isinstance(utterance, str):
            print(f"> {Fore.YELLOW + utterance + Style.RESET_ALL}\n")

        try:
            # LOG.info("just before interprteting...")
            audio_chunk = generator(utterance, last_pressed)
            if audio_chunk:
                stream.feed(audio_chunk)
                if not stream.is_playing():
                    stream.play_async()
        except Exception:
            sys.exit(1)


def stop_speech():
    stream.stop()


def on_press(key):
    global is_pressed, last_pressed, playback_paused
    if key == wake_key and not is_pressed:
        beep("Morse")
        pause_playback()
        playback_paused = True
        is_pressed = True
        last_pressed = time.time()
        recorder.start()

        if stream.is_playing():
            stream.stop()


def on_release(key):
    global is_pressed, last_pressed

    if key == wake_key and is_pressed:
        recorder.stop()
        is_pressed = False


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


async def message_queue_handler():
    LOG.debug("Starting message_queue handler...")
    while True:
        if not from_user.empty():
            LOG.info("Message gotten from user...")
            chunk = await from_user.get()
        elif not from_computer.empty():
            LOG.info("Message gotten from computer...")
            chunk = await from_computer.get()
        else:
            await asyncio.sleep(1)
            continue

        message = accumulator.accumulate(chunk)

        if message is None:
            continue

        if not isinstance(message["content"], str):
            print("This should be a string, but it's not:", message["content"])
            message["content"] = message["content"].decode()

        LOG.info(f"message: {message}")
        process_text(message)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # event_clock = clock()
    beep("Blow")
    # stream.feed("At your service sir.")
    # stream.play_async()
    print("")
    print_markdown("○")
    print_markdown("\n*Ready...*\n")
    print(f"\nPress and hold {wake_key}, speak, then release.\n")
    yield
    LOG.info("Shutting down audio recorder...")
    # event_clock.join()
    # event_clock.stop()
    # recorder.shutdown()
    # stream.feed("Shutting down now sir")
    # stream.play_async()
    print_markdown("*Server is shutting down*")
    LOG.info("Shutting down assistant...")


app = FastAPI(lifespan=lifespan)


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


async def main():
    LOG.info("Starting assistant program...")
    global stream, recorder
    recorder = STT(event).get_recorder()

    # recorder = AudioToTextRecorder()
    stream = TTS(event, playback_paused).stream
    start_notification_observer()
    push_to_talk_listener()
    asyncio.create_task(message_queue_handler())
    # asyncio.create_task(put_kernel_messages_into_queue(from_computer))
    create_daemon(target=speech_listener, args=(recorder,))
    connect_events(event)

    config = Config(app=app, host=HOST, port=PORT, log_level="critical")
    server = Server(config)
    await server.serve()


if __name__ == "__main__":
    # loop = asyncio.get_event_loop()
    # asyncio.set_event_loop(loop)
    asyncio.run(main())
