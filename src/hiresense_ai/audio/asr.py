from elevenlabs.client import ElevenLabs

from hiresense_ai.config import (
    ELEVENLABS_API_KEY,
    ELEVENLABS_STT_LANGUAGE,
    ELEVENLABS_STT_MODEL,
)


class ElevenLabsASR:
    def __init__(self):
        if not ELEVENLABS_API_KEY:
            raise RuntimeError("ELEVENLABS_API_KEY is not set.")
        self.client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    def transcribe(self, audio_file):
        with open(audio_file, "rb") as f:
            response = self.client.speech_to_text.convert(
                file=f,
                model_id=ELEVENLABS_STT_MODEL,
                language_code=ELEVENLABS_STT_LANGUAGE,
            )
        return response.text
