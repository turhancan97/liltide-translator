"""Bounded capture workers for local level checks and the streaming session."""

from dataclasses import dataclass
import math
import multiprocessing as mp
import platform
from queue import Empty, Full
import signal
import time

from liltide.audio import AudioError, SoundCardBackend, backend_hint


@dataclass(frozen=True)
class Levels:
    rms_dbfs: float
    peak_dbfs: float
    clipping: bool


def measure_levels(samples) -> Levels:
    import numpy as np

    data = np.asarray(samples, dtype=np.float64)
    if data.ndim != 2 or not data.size:
        raise AudioError("Capture returned an empty or invalid audio block.")
    if not np.isfinite(data).all():
        raise AudioError("Capture returned non-finite samples; check the device and sample rate.")
    # Measure before downmix so anti-phase stereo cannot hide an active signal.
    peak = float(np.max(np.abs(data)))
    scale = max(1.0, peak)
    rms = scale * float(np.sqrt(np.mean(np.square(data / scale))))
    def db(value):
        return 20 * math.log10(value) if value > 0 else -math.inf
    return Levels(db(rms), db(peak), peak >= 1.0)


def _offer(queue, item):
    # Never queue raw audio or block native capture behind terminal rendering.
    try:
        queue.put_nowait(item)
    except Full:
        pass


def _worker(device_id, source, sample_rate, updates, errors, stop, raw=False):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        backend = SoundCardBackend()
        mic = backend.select(device_id, source)
        frames = sample_rate // 10
        # Read in 100 ms chunks, but let the backend choose a valid native buffer.
        # CoreAudio endpoints may reject a 100 ms hardware block size outright.
        with mic.recorder(samplerate=sample_rate, channels=int(mic.channels)) as recorder:
            while not stop.is_set():
                samples = recorder.record(numframes=frames)
                levels = measure_levels(samples)
                if raw:
                    try:
                        updates.put_nowait(samples)
                    except Full:
                        raise AudioError("Audio gap: capture buffer exceeded one second; session stopped.")
                else:
                    _offer(updates, levels)
    except Exception as exc:
        message = str(exc) if isinstance(exc, AudioError) else (
            f"Capture failed ({type(exc).__name__}). Check --sample-rate and device availability. {backend_hint(platform.system())}"
        )
        _offer(errors, message)


def capture_stream(device_id: str, source: str, sample_rate: int, duration: float | None = None, *, raw=False):
    """Yield levels or raw blocks; bound waits and terminate stuck native readers."""
    ctx = mp.get_context("spawn")
    updates, errors, stop = ctx.Queue(maxsize=10 if raw else 1), ctx.Queue(maxsize=1), ctx.Event()
    worker = ctx.Process(target=_worker, args=(device_id, source, sample_rate, updates, errors, stop, raw), daemon=True)
    started = False
    try:
        worker.start()
        started = True
        last = time.monotonic()
        received = False
        while True:
            now = time.monotonic()
            if duration is not None and received and now - first >= duration:
                return
            try:
                raise AudioError(errors.get_nowait())
            except Empty:
                pass
            try:
                levels = updates.get(timeout=0.1)
            except Empty:
                if not worker.is_alive():
                    # Give the queue feeder a bounded chance to deliver its error.
                    try:
                        raise AudioError(errors.get(timeout=0.2))
                    except Empty:
                        raise AudioError("Audio worker exited unexpectedly; run 'liltide doctor'.")
                timeout = 8 if received else 15
                if now - last > timeout:
                    raise AudioError("No audio frames received. Check capture permissions, playback, and device routing.")
                if raw:
                    yield None  # Allow event rendering and keyboard controls during startup.
                continue
            if not received:
                first = time.monotonic()
            received = True
            last = time.monotonic()
            yield levels
    finally:
        stop.set()
        if started:
            worker.join(timeout=2)
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=2)
        for queue in (updates, errors):
            queue.close()
            queue.cancel_join_thread()


def capture_levels(device_id: str, source: str, sample_rate: int, duration: float | None = None):
    yield from capture_stream(device_id, source, sample_rate, duration)
