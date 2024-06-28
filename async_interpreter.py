import time
import traceback
from core import LOG
from core.util.beeps import beeper
from profiles.mac_os import interpreter


def generator(utterance, last_pressed):
    LOG.info(f"timeout for push-to-talk: {time.time() - last_pressed}")
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
