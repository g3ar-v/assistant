from RealtimeTTS import OpenAIEngine, ElevenlabsEngine, TextToAudioStream
from core import Configuration, LOG


config = Configuration.get()
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
    LOG.info(f"Accessing elevenlabs voice: {TTS_CONFIG.get('elevenlabs').get('voice')}")
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
