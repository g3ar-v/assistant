from RealtimeTTS import OpenAIEngine, ElevenlabsEngine, TextToAudioStream
from core import Configuration, LOG

from core.util.spotify import play_playback, pause_playback


class TTSEngineFactory:
    def __init__(self):
        self.config = Configuration.get()
        self.engine = None
        self.TTS_CONFIG = self.config.get("tts")
        self._initialize_engine()

    def _initialize_engine(self):
        module = self.TTS_CONFIG.get("module")
        if module == "elevenlabs":
            self._initialize_elevenlabs_engine()
        elif module == "openai":
            self._initialize_openai_engine()
        LOG.info(f"Accessing tts module: {module}")

    def _initialize_elevenlabs_engine(self):
        elevenlabs_config = self.TTS_CONFIG.get("elevenlabs")
        voice = elevenlabs_config.get("voice")
        LOG.info(f"Accessing elevenlabs voice: {voice}")
        LOG.info(f"Accessing elevenlabs api_key: {elevenlabs_config.get('api_key')}")
        LOG.info(
            f"Accessing elevenlabs stability: {elevenlabs_config.get(voice).get('stability')}"
        )
        LOG.info(
            f"Accessing elevenlabs clarity: {elevenlabs_config.get(voice).get('similarity_boost')}"
        )
        self.engine = ElevenlabsEngine(
            api_key=elevenlabs_config.get("api_key"),
            voice=voice,
            id=elevenlabs_config.get(voice).get("id"),
            stability=elevenlabs_config.get(voice).get("stability"),
            clarity=elevenlabs_config.get(voice).get("similarity_boost"),
        )

    def _initialize_openai_engine(self):
        openai_config = self.TTS_CONFIG.get("openai")
        LOG.info(f"Accessing openai model: {openai_config.get('model')}")
        LOG.info(f"Accessing openai voice: {openai_config.get('voice')}")
        self.engine = OpenAIEngine(
            model=openai_config.get("model"),
            voice=openai_config.get("voice"),
        )

    def get_engine(self):
        return self.engine


class TTS:
    def __init__(self, event, playback_paused):
        # Instantiate the factory to initialize the engine
        self.playback_paused = playback_paused
        self.tts_engine = TTSEngineFactory().get_engine()
        self.stream = TextToAudioStream(
            engine=self.tts_engine, on_audio_stream_stop=self.on_speaking_end
        )

    def on_speaking_end(self):
        # global playback_paused
        if self.playback_paused:
            play_playback()
            self.playback_paused = False
