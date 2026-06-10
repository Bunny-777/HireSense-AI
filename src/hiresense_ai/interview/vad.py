from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class VADConfig:
    energy_threshold: float = 0.015


@dataclass
class VADResult:
    is_speech: bool
    rms_energy: float


class EnergyVAD:
    def __init__(self, config: VADConfig):
        self.config = config

    def detect(self, audio_chunk: np.ndarray) -> VADResult:
        if audio_chunk.size == 0:
            return VADResult(is_speech=False, rms_energy=0.0)

        rms = float(np.sqrt(np.mean(np.square(audio_chunk))))
        return VADResult(
            is_speech=rms >= self.config.energy_threshold,
            rms_energy=rms,
        )
