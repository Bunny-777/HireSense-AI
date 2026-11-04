from pathlib import Path
import httpx
from elevenlabs.client import ElevenLabs

from hiresense_ai.config import (
    ELEVENLABS_API_KEY,
    ELEVENLABS_STT_LANGUAGE,
    ELEVENLABS_STT_MODEL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
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


class GroqASR:
    """Uses Groq's fast Whisper API (whisper-large-v3-turbo) for Speech-to-Text."""
    def __init__(self, api_key: str = OPENAI_API_KEY, base_url: str = OPENAI_BASE_URL):
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY / Groq API key is not set.")
        self.api_key = api_key
        self.base_url = base_url

    def transcribe(self, audio_file):
        with open(audio_file, "rb") as f:
            files = {"file": (Path(audio_file).name, f, "audio/wav")}
            data = {"model": "whisper-large-v3-turbo", "language": ELEVENLABS_STT_LANGUAGE or "en"}
            r = httpx.post(
                f"{self.base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files=files,
                data=data,
                timeout=30,
            )
            r.raise_for_status()
            return r.json().get("text", "")


def get_asr():
    """Returns ElevenLabs ASR if configured, otherwise falls back to Groq/OpenAI Whisper."""
    if ELEVENLABS_API_KEY:
        return ElevenLabsASR()
    if OPENAI_API_KEY:
        return GroqASR()
    raise RuntimeError(
        "No STT API key configured. Please set ELEVENLABS_API_KEY or OPENAI_API_KEY (Groq) in .env."
    )
