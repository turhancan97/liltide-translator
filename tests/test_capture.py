from queue import Queue
from threading import Event
from types import SimpleNamespace

import numpy as np

from liltide import capture


def test_worker_captures_all_channels_and_closes(monkeypatch):
    stop, updates, errors = Event(), Queue(maxsize=1), Queue(maxsize=1)
    calls, closed = [], []
    class Recorder:
        def __enter__(self):
            return self
        def record(self, numframes):
            assert numframes == 4800
            stop.set()
            return np.full((numframes, 2), .25)
        def __exit__(self, *args):
            closed.append(True)
    def recorder(**kwargs):
        calls.append(kwargs)
        return Recorder()
    monkeypatch.setattr(capture, "SoundCardBackend", lambda: SimpleNamespace(
        select=lambda *a: SimpleNamespace(channels=2, recorder=recorder)))
    monkeypatch.setattr(capture.signal, "signal", lambda *a: None)
    capture._worker("id", "system", 48000, updates, errors, stop)
    assert calls == [{"samplerate": 48000, "channels": 2}]
    assert closed and errors.empty()
    assert updates.get().rms_dbfs < 0


def test_full_display_queue_does_not_block_capture():
    queue = Queue(maxsize=1)
    capture._offer(queue, "first")
    capture._offer(queue, "second")
    assert queue.qsize() == 1


def test_raw_capture_overflow_reports_gap_instead_of_dropping_audio(monkeypatch):
    stop, updates, errors = Event(), Queue(maxsize=1), Queue(maxsize=1)
    updates.put("occupied")
    class Recorder:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            stop.set()
        def record(self, **kwargs):
            return np.zeros((4800, 2), dtype=np.float32)
    monkeypatch.setattr(capture, "SoundCardBackend", lambda: SimpleNamespace(
        select=lambda *a: SimpleNamespace(channels=2, recorder=lambda **kw: Recorder())))
    monkeypatch.setattr(capture.signal, "signal", lambda *a: None)
    capture._worker("id", "system", 48000, updates, errors, stop, raw=True)
    assert "Audio gap" in errors.get_nowait()
    assert stop.is_set()


def test_worker_errors_do_not_leak_native_messages(monkeypatch):
    def bad_backend():
        raise RuntimeError("private native diagnostic")
    monkeypatch.setattr(capture, "SoundCardBackend", bad_backend)
    monkeypatch.setattr(capture.signal, "signal", lambda *a: None)
    errors = Queue(maxsize=1)
    capture._worker("id", "system", 48000, Queue(maxsize=1), errors, Event())
    assert "private native" not in errors.get()


def test_stalled_reader_is_terminated_and_queues_closed(monkeypatch):
    """Native record() may block forever; the parent must still release it."""
    calls = []
    class FakeQueue:
        def get(self, **kwargs):
            raise capture.Empty
        def get_nowait(self):
            raise capture.Empty
        def close(self):
            calls.append("closed")
        def cancel_join_thread(self):
            pass
    class Process:
        def start(self):
            calls.append("started")
        def is_alive(self):
            return True
        def join(self, timeout):
            calls.append(("join", timeout))
        def terminate(self):
            calls.append("terminated")
    class Stop:
        def set(self):
            calls.append("stop")
    ctx = SimpleNamespace(Queue=lambda **kwargs: FakeQueue(), Event=Stop,
                          Process=lambda **kwargs: Process())
    monkeypatch.setattr(capture.mp, "get_context", lambda method: ctx)
    ticks = iter([0, 16])
    monkeypatch.setattr(capture.time, "monotonic", lambda: next(ticks))
    import pytest
    from liltide.audio import AudioError
    with pytest.raises(AudioError, match="No audio frames"):
        next(capture.capture_levels("id", "system", 48000))
    assert "stop" in calls and "terminated" in calls
    assert calls.count("closed") == 2
    assert calls.count(("join", 2)) == 2
