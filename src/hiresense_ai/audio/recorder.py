from __future__ import annotations

import json
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from hiresense_ai.interview.vad import EnergyVAD, VADConfig


@dataclass
class RecorderConfig:
    sample_rate: int = 16000
    silence_seconds: float = 1.1
    max_seconds: float = 45.0
    input_device: int | None = None
    vad_threshold: float = 0.015


class MetricsLogger:
    def __init__(self, path: str = "metrics.jsonl"):
        self.path = Path(path)

    def log_turn(
        self,
        transcript: str,
        response: str,
        recording_seconds: float,
        transcription_ms: float,
        followup_ms: float,
        followup_ms_raw: float,
    ) -> None:
        payload = {
            "timestamp": time.time(),
            "transcript": transcript,
            "response": response,
            "recording_seconds": round(recording_seconds, 2),
            "transcription_ms": round(transcription_ms, 2),
            "followup_ms": round(followup_ms, 2),
            "followup_ms_raw": round(followup_ms_raw, 2),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")


class MicrophoneRecorder:
    def __init__(self, config: RecorderConfig):
        self.config = config
        self.vad = EnergyVAD(VADConfig(energy_threshold=config.vad_threshold))

    def record_until_silence(self) -> tuple[Path, float]:
        blocksize = int(self.config.sample_rate * 0.1)
        silence_blocks = max(1, int(self.config.silence_seconds / 0.1))
        started = False
        silent_count = 0
        captured: list[np.ndarray] = []
        speech_start = None

        print("\nListening... start speaking.")
        with sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=blocksize,
            device=self.config.input_device,
        ) as stream:
            while True:
                chunk, _ = stream.read(blocksize)
                mono = np.asarray(chunk).reshape(-1)
                is_speech = self.vad.detect(mono).is_speech
                if is_speech and not started:
                    print("Speech detected by VAD. Recording...")
                    started = True
                    speech_start = time.monotonic()
                if started:
                    captured.append(mono.copy())
                    silent_count = 0 if is_speech else silent_count + 1
                    elapsed = time.monotonic() - speech_start
                    if elapsed >= self.config.max_seconds or silent_count >= silence_blocks:
                        break

        audio = np.concatenate(captured) if captured else np.zeros(0, dtype=np.float32)
        if audio.size == 0:
            raise RuntimeError("No audio captured.")
        handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        path = Path(handle.name)
        handle.close()
        sf.write(path, audio, self.config.sample_rate)
        return path, audio.size / self.config.sample_rate
