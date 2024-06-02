# import time
import asyncio

import os
import time
import traceback

import colorama
from colorama import Fore, Style
from fastapi import FastAPI, Request
from pynput import keyboard
from uvicorn import Config, Server

from core import Configuration, LOG
from core.util.accumulator import Accumulator
from core.util.audio_utils import find_input_device
from core.util.beeps import beep, beeper
from core.util.process_utils import create_daemon

# from core.util.log import LOG
from core.util.spotify import reduce_playback_volume, restore_playback_volume
from core.util.print_markdown import print_markdown
from intercept_notification import start_notification_observer
from profiles.default import interpreter

accumulator = Accumulator()

# Server
app = FastAPI()
from_user = asyncio.Queue()
HOST = "0.0.0.0"
PORT = 8008

wake_key = keyboard.Key.f8

# Button state
is_pressed = False
last_pressed = 0


colorama.init()

full_sentences = []
displayed_text = ""


def clear_console():
    os.system("clear" if os.name == "posix" else "cls")


def text_detected(text):
    global displayed_text
    sentences_with_style = [
        f"{Fore.YELLOW + sentence + Style.RESET_ALL if i % 2 == 0 else Fore.CYAN + sentence + Style.RESET_ALL} "
        for i, sentence in enumerate(full_sentences)
    ]
    new_text = (
        "".join(sentences_with_style).strip() + " " + text
        if len(sentences_with_style) > 0
        else text
    )

    if new_text != displayed_text:
        displayed_text = new_text
        clear_console()
        print(displayed_text, end="\n", flush=True)


# @app.on_event("startup")
# async def startup_event():
#     # server_url = f"{HOST}:{PORT}"
#     print("")
#     print_markdown("○")
#     print_markdown("\n*Starting...*\n")
#     print("")


# @app.on_event("shutdown")
# async def shutdown_event():
#     print_markdown("*Server is shutting down*")
#     LOG.info("Shutting down...")


@app.post("/")
async def add_computer_message(request: Request):
    body = await request.json()
    text = body.get("text")
    if not text:
        return {"error": "Missing 'text' in request body"}, 422
    message = {"role": "user", "type": "message", "content": text}
    await from_user.put({"role": "user", "type": "message", "start": True})
    await from_user.put(message)
    await from_user.put({"role": "user", "type": "message", "end": True})


def process_text(utterance):
    # only STT returns str
    # notification thread and websocket returns dict
    if isinstance(utterance, str):
        print(f"> {utterance}\n")
    else:
        print(f"> {utterance['content']}")

    #     full_sentences.append(text)
    #     text_detected("")

    stream.feed(generator(utterance))
    stream.play_async()


def generator(utterance):
    global last_pressed

    if time.time() - last_pressed > 0.25:
        try:
            old_last_pressed = last_pressed
            for chunk in interpreter.chat(utterance, display=True, stream=True):
                # Halt current execution to process new speech utterance
                if old_last_pressed != last_pressed:
                    beeper.stop()
                    break

                content = chunk.get("content")

                if chunk.get("type") == "message":
                    if content:
                        beeper.stop()

                        # Experimental: The AI voice sounds better with replacements like these, but it should happen at the TTS layer
                        # content = content.replace(". ", ". ... ").replace(", ", ", ... ").replace("!", "! ... ").replace("?", "? ... ")

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


# stream.feed("Hi, how can I help you?")
# stream.play_async()


def on_press(key):
    global is_pressed, last_pressed
    if key == wake_key and not is_pressed:
        beep("Morse")
        reduce_playback_volume()
        is_pressed = True
        last_pressed = time.time()
        recorder.start()
        stream.stop()


def on_release(key):
    global is_pressed, last_pressed

    if key == wake_key and is_pressed:
        recorder.stop()
        is_pressed = False
        # beep("Frog")
        # restore_playback_volume()


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


async def websocket_listener():
    LOG.info("Starting websocket listener...")
    while True:
        if not from_user.empty():
            LOG.info("Message gotten from websocket...")
            chunk = await from_user.get()
            # break
        else:
            await asyncio.sleep(1)
            continue
        # await asyncio.sleep(0.1)

        # chunk = ""
        message = accumulator.accumulate(chunk)

        if message is None:
            continue

        if type(message["content"]) != str:
            print("This should be a string, but it's not:", message["content"])
            message["content"] = message["content"].decode()

        LOG.info(f"message from websocket: {message}")
        process_text(message)


async def main():
    beep("Blow")
    start_notification_observer()
    push_to_talk_listener()
    asyncio.create_task(websocket_listener())
    create_daemon(target=speech_listener, args=(recorder,))

    config = Config(app=app, host=HOST, port=PORT, lifespan="on", log_level="info")
    server = Server(config)
    print(f"\nPress and hold {wake_key}, speak, then release.\n")
    await server.serve()


if __name__ == "__main__":
    from RealtimeSTT import AudioToTextRecorder
    from RealtimeTTS import OpenAIEngine, TextToAudioStream

    LOG.info("\n")
    LOG.info("Starting assistant program...")
    config = Configuration.get()

    LISTENER_CONFIG = config.get("listener")
    device_name = LISTENER_CONFIG.get("device_name")
    LOG.debug("Using device: {}".format(device_name))
    LOG.info("Wakeword: {}".format(LISTENER_CONFIG.get("wake_word")))
    LOG.debug(
        "Whisper model: {}".format(
            LISTENER_CONFIG.get("stt").get("whisper").get("model")
        )
    )

    def on_wakeword_detected():
        print("\nWake word detected\n")
        # LOG.info("Wake word detected")
        beep("Morse")
        stream.stop()
        reduce_playback_volume()

    def on_recording_stop():
        beep("Frog")
        restore_playback_volume()

    def on_wakeword_timeout():
        recorder.stop()

    device_index = find_input_device(device_name)
    recorder_config = {
        "wake_words": LISTENER_CONFIG.get("wake_word"),
        "model": LISTENER_CONFIG.get("stt").get("whisper").get("model"),
        "language": "en",
        "input_device_index": device_index,
        "porcupine_access_token": config.get("microservices").get("porcupine_api_key"),
        "spinner": False,
        "on_wakeword_detected": on_wakeword_detected,
        "pre_recording_buffer_duration": 1,
        "on_recording_stop": on_recording_stop,
        "on_wakeword_timeout": on_wakeword_timeout,
        # "silero_sensitivity": 0.4,
        # "webrtc_sensitivity": 2,
        "level": 20,
        # "post_speech_silence_duration": 1.0,
        # "min_length_of_recording": 0,
        # "min_gap_between_recordings": 0,
        # "enable_realtime_transcription": True,
        # "realtime_processing_pause": 0.2,
        # "realtime_model_type": LISTENER_CONFIG.get("stt").get("whisper").get("model"),
        # "on_realtime_transcription_update": text_detected,
    }
    recorder = AudioToTextRecorder(**recorder_config)
    # recorder = None

    stream = TextToAudioStream(OpenAIEngine())
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    asyncio.run(main())
