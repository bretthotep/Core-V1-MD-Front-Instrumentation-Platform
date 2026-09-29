"""Audio input abstraction for the visualiser.

Today only :class:`MockAudioSource` exists. A future ``WasapiLoopbackSource``
will capture the system mix on Windows and run an FFT; it only needs to
implement :meth:`AudioSource.read_frame`.
"""

from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod

from telemetry.models import AudioFrame


class AudioSource(ABC):
    bands: int = 32
    samples: int = 128

    def start(self) -> None:  # noqa: B027 - optional hook
        pass

    def stop(self) -> None:  # noqa: B027 - optional hook
        pass

    @abstractmethod
    def read_frame(self, now: float) -> AudioFrame:
        """Return the most recent analysed frame."""


class MockAudioSource(AudioSource):
    """Synthetic music-like signal: a beat, a bass line and some shimmer."""

    def __init__(self, bands: int = 32, samples: int = 128, bpm: float = 118.0, seed: int | None = 7) -> None:
        self.bands = bands
        self.samples = samples
        self.bpm = bpm
        self._rng = random.Random(seed)
        self._smoothed = [0.0] * bands

    def read_frame(self, now: float) -> AudioFrame:
        beat_phase = (now * self.bpm / 60.0) % 1.0
        kick = math.exp(-beat_phase * 7.0)
        spectrum = []
        for i in range(self.bands):
            x = i / max(1, self.bands - 1)
            base = 0.75 * (1.0 - x) ** 1.6 * (0.35 + 0.65 * kick)
            melody = 0.35 * max(0.0, math.sin(now * 2.1 + x * 9.0)) * (1.0 - 0.5 * x)
            air = 0.12 * self._rng.random() * x
            target = min(1.0, base + melody + air)
            # EL-style ballistics: fast attack, slow release
            prev = self._smoothed[i]
            self._smoothed[i] = target if target > prev else prev * 0.86 + target * 0.14
            spectrum.append(self._smoothed[i])
        waveform = tuple(
            0.6 * kick * math.sin(2 * math.pi * (3 * t / self.samples) + now * 12)
            + 0.25 * math.sin(2 * math.pi * (11 * t / self.samples) + now * 5)
            + 0.05 * (self._rng.random() - 0.5)
            for t in range(self.samples)
        )
        return AudioFrame(spectrum=tuple(spectrum), waveform=waveform, peak=max(spectrum, default=0.0))
