"""Shared streaming audio normalization; no network or persistence."""

import numpy as np
import soxr

from liltide.audio import AudioError


class PCMEncoder:
    """Downmix and statefully resample float audio into 16 kHz little-endian PCM16."""

    def __init__(self, rate: int):
        self.resampler = soxr.ResampleStream(rate, 16000, 1, dtype="float32", quality="HQ")

    def encode(self, samples, *, last=False) -> bytes:
        data = np.asarray(samples)
        if data.ndim != 2 or data.shape[1] < 1 or not np.isfinite(data).all():
            raise AudioError("Invalid/non-finite audio samples; transmission stopped.")
        mono = np.clip(data.mean(axis=1, dtype=np.float64), -1, 1).astype(np.float32)
        output = self.resampler.resample_chunk(mono, last=last)
        return np.rint(np.clip(output, -1, 1 - 1 / 32768) * 32768).astype("<i2").tobytes()

    def flush(self) -> bytes:
        return self.encode(np.empty((0, 1), dtype=np.float32), last=True)
