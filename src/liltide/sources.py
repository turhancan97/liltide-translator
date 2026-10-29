"""Polling source adapters so the session can handle controls without GUI dependencies."""

import time
import wave

import numpy as np

from liltide.audio import AudioError
from liltide.capture import capture_stream


class LiveSource:
    def __init__(self, device, source, rate):
        self.rate = rate
        self.stream = capture_stream(device, source, rate, raw=True)

    def read(self):
        return next(self.stream)

    def resume(self):
        pass

    def close(self):
        self.stream.close()


class WaveSource:
    def __init__(self, path):
        try:
            self.file = wave.open(str(path), "rb")
        except (OSError, wave.Error, EOFError) as exc:
            raise AudioError("Cannot open WAV input. Use an existing uncompressed PCM16 WAV file.") from exc
        self.rate = self.file.getframerate()
        self.channels = self.file.getnchannels()
        if self.file.getsampwidth() != 2 or self.channels not in (1, 2) or not 8000 <= self.rate <= 192000:
            self.file.close()
            raise AudioError("WAV must be PCM16 mono/stereo at 8000–192000 Hz.")
        self.frames = max(1, self.rate // 10)
        self.resume()

    def resume(self):
        # Retain the file cursor; discard paused wall time from replay pacing.
        self.next_read = time.monotonic()

    def read(self):
        if time.monotonic() < self.next_read:
            return None
        try:
            data = self.file.readframes(self.frames)
        except (OSError, wave.Error) as exc:
            raise AudioError("WAV read failed.") from exc
        if not data:
            raise StopIteration
        if len(data) % (2 * self.channels):
            raise AudioError("WAV contains a truncated PCM frame.")
        samples = np.frombuffer(data, dtype="<i2").reshape(-1, self.channels).astype(np.float32) / 32768
        # Avoid catch-up bursts if a consumer is temporarily slow.
        self.next_read = time.monotonic() + len(samples) / self.rate
        return samples

    def close(self):
        self.file.close()
