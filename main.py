# import time
# import traceback
import asyncio
import sys
from pynput import keyboard
from RealtimeSTT import AudioToTextRecorder
from RealtimeTTS import TextToAudioStream, OpenAIEngine
from inflect import engine
from utils import find_input_device
from utils.beeps import beep, beeper
from utils.log import LOG
from config import Configuration

LOG.init()

config = Configuration.get()
LISTENER_CONFIG = config.get("listener")
device_name = LISTENER_CONFIG.get("device_name")
LOG.debug("Using device: {}".format(device_name))

# FIXME: LOG doesn't seem to work in the script for some fucntions
if __name__ == "__main__":
    from profiles.default import interpreter

    wake_key = keyboard.Key.f8

    device_index = find_input_device(device_name)
    LOG.info("Wakeword: {}".format(LISTENER_CONFIG.get("wake_word")))
    LOG.info(
        "Whisper model: {}".format(
            LISTENER_CONFIG.get("stt").get("whisper").get("model")
        )
    )
    engine = OpenAIEngine()
    stream = TextToAudioStream(engine)

    def on_wakeword_detected():
        print("Wake word detected")
        # LOG.info("Wake word detected")
        beep("Morse")
        stream.stop()

    def on_recording_stop():
        beep("Frog")

    def process_text(utterance):
        # print(text)
        print("Utterance: {}".format(utterance))
        # LOG.info("Utterance: {}".format(utterance))
        stream.feed(generator(utterance))
        stream.play_async()

    def generator(utterance):
        try:
            for chunk in interpreter.chat(utterance, display=True, stream=True):
                # if old_last_pressed != last_pressed:
                #     beeper.stop()
                #     break

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
        except KeyboardInterrupt:
            raise
        # except:
        #     LOG.exception(traceback.format_exec())

    beep("Blow")
    # stream.feed("Hi, how can I help you?")
    # stream.play_async()

    recorder_config = {
        "wake_words": LISTENER_CONFIG.get("wake_word"),
        "model": LISTENER_CONFIG.get("stt").get("whisper").get("model"),
        "language": "en",
        "input_device_index": device_index,
        "porcupine_access_token": config.get("microservices").get("porcupine_api_key"),
        "spinner": False,
        "on_wakeword_detected": on_wakeword_detected,
        "pre_recording_buffer_duration": 3,
        "on_recording_stop": on_recording_stop,
    }
    recorder = AudioToTextRecorder(**recorder_config)

    def on_press(key):
        if key == wake_key:
            # beep("Morse")
            recorder.start()
            stream.stop()

    def on_release(key):
        if key == wake_key:
            recorder.stop()

    async def start_keyboard_listener():
        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()

    asyncio.run(start_keyboard_listener())

    while True:
        try:
            recorder.text(process_text)

        except KeyboardInterrupt:
            LOG.info("Shutting down...")
            stream.feed("Shutting down... Goodbye Sir, it was a pleasure.")
            stream.play()
            sys.exit(0)
