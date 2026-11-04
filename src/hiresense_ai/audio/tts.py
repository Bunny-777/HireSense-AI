import io
import subprocess

import sounddevice as sd
import soundfile as sf
from elevenlabs.client import ElevenLabs

from hiresense_ai.config import ELEVENLABS_API_KEY, ELEVENLABS_TTS_MODEL, ELEVENLABS_VOICE_ID

FALLBACK_VOICE_IDS = (
    ELEVENLABS_VOICE_ID,
    "EXAVITQu4vr4xnSDxMaL",
    "TxGEqnHWrfWFTfGW9XjX",
)


class ElevenLabsSpeaker:
    def __init__(self):
        if not ELEVENLABS_API_KEY:
            raise RuntimeError("ELEVENLABS_API_KEY is not set.")
        self.client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    def speak(self, text):
        data, samplerate = sf.read(io.BytesIO(self._synthesize(text)))
        sd.play(data, samplerate)
        sd.wait()

    def _synthesize(self, text):
        for voice_id in FALLBACK_VOICE_IDS:
            try:
                return b"".join(
                    self.client.text_to_speech.convert(
                        text=text,
                        voice_id=voice_id,
                        model_id=ELEVENLABS_TTS_MODEL,
                    )
                )
            except Exception:
                pass
        raise RuntimeError("ElevenLabs TTS failed for all configured voice ids.")


class SystemSpeaker:
    """Uses Windows built-in speech synthesizer for local voice output without any API key."""
    def speak(self, text: str) -> None:
        clean = text.replace('"', '""').replace("'", "''")
        cmd = f'Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $synth.Speak("{clean}")'
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True)


def get_speaker(no_tts: bool = False):
    """Returns ElevenLabs speaker if key is present, otherwise falls back to Windows system speaker."""
    if no_tts:
        return None
    if ELEVENLABS_API_KEY:
        try:
            return ElevenLabsSpeaker()
        except Exception:
            return SystemSpeaker()
    return SystemSpeaker()
