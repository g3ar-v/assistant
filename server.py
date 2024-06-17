# import time
import asyncio
from contextlib import asynccontextmanager
import json
import sys

import time
import traceback

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from pynput import keyboard
from uvicorn import Config, Server

from core import Configuration, LOG
from core.util.accumulator import Accumulator
from core.util.audio_utils import find_input_device
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
    print("")
    print_markdown("○")
    print_markdown("\n*Ready...*\n")
    print(f"\nPress and hold {wake_key}, speak, then release.\n")
    yield
    LOG.info("Shutting down audio recorder...")
    # recorder.shutdown()
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


def process_text(utterance):
    if isinstance(utterance, str):
        print(f"> {utterance}\n")

    try:
        stream.feed(generator(utterance))
        stream.play_async()
    except Exception:
        sys.exit(1)
        # return


def generator(utterance):
    global last_pressed

    if time.time() - last_pressed > 0.25:
        try:
            old_last_pressed = last_pressed
            for chunk in interpreter.chat(utterance, display=True, stream=True):
                # Halt current execution to process new speech utterance
                if old_last_pressed != last_pressed:
                    beeper.stop()
                    LOG.info("Not running due to premature keypress")
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
    asyncio.create_task(put_kernel_messages_into_queue(from_computer))
    create_daemon(target=speech_listener, args=(recorder,))

    config = Config(app=app, host=HOST, port=PORT, log_level="critical")
    server = Server(config)
    await server.serve()


if __name__ == "__main__":
    # from RealtimeSTT import AudioToTextRecorder

    from audio_recorder import AudioToTextRecorder
    from RealtimeTTS import OpenAIEngine, ElevenlabsEngine, TextToAudioStream

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
        # reduce_playback_volume()
        pause_playback()

    def on_transcription_start():
        LOG.info("audio recording is transcribing...")

    def on_recording_stop():
        beep("Frog")

    def on_wakeword_timeout():
        LOG.info("STOPPED RECORDING DUE TO TIMEOUT")
        recorder.stop()

    # device_index = find_input_device(device_name)
    recorder_config = {
        "wake_words": LISTENER_CONFIG.get("wake_word"),
        "model": LISTENER_CONFIG.get("stt").get("whisper").get("model"),
        "language": "en",
        # "input_device_index": device_index,
        "spinner": False,
        "porcupine_access_token": config.get("microservices").get("porcupine_api_key"),
        "on_wakeword_detected": on_wakeword_detected,
        "pre_recording_buffer_duration": 3,
        "on_recording_stop": on_recording_stop,
        "on_wakeword_timeout": on_wakeword_timeout,
        "on_transcription_start": on_transcription_start,
        "wake_word_timeout": 1.5,
        # "silero_sensitivity": 0.4,
        # "webrtc_sensitivity": 2,
        # "post_speech_silence_duration": 1.0,
        "min_length_of_recording": 0,
        # "min_gap_between_recordings": 0,
        # "enable_realtime_transcription": True,
        # "realtime_processing_pause": 0.2,
        # "realtime_model_type": LISTENER_CONFIG.get("stt").get("whisper").get("model"),
        # "on_realtime_transcription_update": text_detected,
    }
    recorder = AudioToTextRecorder(**recorder_config)

    engine = None
    TTS_CONFIG = config.get("tts")
    if TTS_CONFIG.get("module") == "elevenlabs":
        voice = TTS_CONFIG.get("elevenlabs").get("voice")
        engine = ElevenlabsEngine(
            api_key=TTS_CONFIG.get("elevenlabs").get("api_key"),
            voice=voice,
            stability=TTS_CONFIG.get("elevenlabs").get(voice).get("stability"),
            clarity=TTS_CONFIG.get("elevenlabs").get(voice).get("clarity"),
        )
    LOG.info(f"Accessing tts module: {TTS_CONFIG.get('module')}")
    if TTS_CONFIG.get("module") == "elevenlabs":
        LOG.info(
            f"Accessing elevenlabs voice: {TTS_CONFIG.get('elevenlabs').get('voice')}"
        )
        voice = TTS_CONFIG.get("elevenlabs").get("voice")
        LOG.info(
            f"Accessing elevenlabs api_key: {TTS_CONFIG.get('elevenlabs').get('api_key')}"
        )
        LOG.info(
            f"Accessing elevenlabs stability: {TTS_CONFIG.get('elevenlabs').get(voice).get('stability')}"
        )
        LOG.info(
            f"Accessing elevenlabs clarity: {TTS_CONFIG.get('elevenlabs').get(voice).get('similarity_boost')}"
        )
        engine = ElevenlabsEngine(
            api_key=TTS_CONFIG.get("elevenlabs").get("api_key"),
            voice=voice,
            id=TTS_CONFIG.get("elevenlabs").get(voice).get("id"),
            stability=TTS_CONFIG.get("elevenlabs").get(voice).get("stability"),
            clarity=TTS_CONFIG.get("elevenlabs").get(voice).get("similarity_boost"),
        )
    elif TTS_CONFIG.get("module") == "openai":
        LOG.info(f"Accessing openai model: {TTS_CONFIG.get('openai').get('model')}")
        LOG.info(f"Accessing openai voice: {TTS_CONFIG.get('openai').get('voice')}")
        engine = OpenAIEngine(
            model=TTS_CONFIG.get("openai").get("model"),
            voice=TTS_CONFIG.get("openai").get("voice"),
        )

    stream = TextToAudioStream(engine=engine, on_audio_stream_stop=on_speaking_end)
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        LOG.info("Shutting down...")
