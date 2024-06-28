from core import Configuration
from core.util.log import LOG
from core.util.beeps import beep
from core.util.audio_utils import find_input_device
from core.util.spotify import pause_playback

# from .audio_recorder import AudioToTextRecorder
from RealtimeSTT import AudioToTextRecorder

config = Configuration.get()


class STT:
    def __init__(self, event) -> None:
        self.event = event
        LISTENER_CONFIG = config.get("listener")
        device_name = LISTENER_CONFIG.get("device_name")
        LOG.debug("Using device: {}".format(device_name))
        device_index = find_input_device(device_name)
        LOG.info("Wakeword: {}".format(LISTENER_CONFIG.get("wake_word")))
        LOG.debug(
            "Whisper model: {}".format(
                LISTENER_CONFIG.get("stt").get("whisper").get("model")
            )
        )
        self.recorder_config = {
            "wake_words": LISTENER_CONFIG.get("wake_word"),
            "model": LISTENER_CONFIG.get("stt").get("whisper").get("model"),
            "language": "en",
            "input_device_index": device_index,
            "spinner": False,
            "porcupine_access_token": config.get("microservices").get(
                "porcupine_api_key"
            ),
            "on_wakeword_detected": self.on_wakeword_detected,
            "pre_recording_buffer_duration": 3,
            "on_recording_stop": self.on_recording_stop,
            "on_wakeword_timeout": self.on_wakeword_timeout,
            "on_transcription_start": self.on_transcription_start,
            "wake_word_timeout": 1.5,
            # "silero_sensitivity": 0.4,
            # "webrtc_sensitivity": 2,
            # "post_speech_silence_duration": 1.0,
            "min_length_of_recording": 2,
            # "min_gap_between_recordings": 0,
            # "enable_realtime_transcription": True,
            # "realtime_processing_pause": 0.2,
            # "realtime_model_type": LISTENER_CONFIG.get("stt").get("whisper").get("model"),
            # "on_realtime_transcription_update": text_detected,
        }
        self.recorder = AudioToTextRecorder(**self.recorder_config)
        # self.recorder.stop()

    def connect_events(self):
        self.event.on("recording.stop", self.recorder.stop())

    def on_wakeword_detected(self):
        print("\nWake word detected\n")
        beep("Morse")
        self.event.emit("stream.stop")
        # stream.stop()
        pause_playback()

    def on_transcription_start(self):
        LOG.info("audio recording is transcribing...")

    def on_recording_stop(self):
        beep("Frog")

    def on_wakeword_timeout(self):
        LOG.info("STOPPED RECORDING DUE TO TIMEOUT")
        # recorder.stop()
        self.event.emit("recording.stop")

    def get_recorder(self):
        return self.recorder
