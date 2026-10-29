from queue import Queue
from threading import Event
from types import SimpleNamespace

import numpy as np
import pytest

from liltide import capture
from liltide.audio import AudioError, InputIdentity, SoundCardBackend


@pytest.mark.parametrize("renumbered", [False, True], ids=["disappeared", "same-device-new-id"])
def test_device_changes_after_parent_preflight_fail_before_recorder(monkeypatch, renumbered):
    """Model a topology change across preflight/capture, without native audio."""
    recorder_calls = []
    def recorder(**kwargs):
        recorder_calls.append(kwargs)
        raise AssertionError("An unmatched device must never be opened")
    original = SimpleNamespace(id=101, name="Synthetic virtual input", channels=2,
                               uid="synthetic-persistent-uid", recorder=recorder)
    replacement = SimpleNamespace(id=202, name=original.name, channels=2,
                                  uid=original.uid, recorder=recorder)
    def backend(devices):
        instance = SoundCardBackend.__new__(SoundCardBackend)
        instance.system = "Darwin"
        instance.sc = SimpleNamespace(all_microphones=lambda **kwargs: devices)
        instance._uid = lambda item: item.uid
        return instance
    parent = backend([original])
    selected = parent.devices()[0].id
    assert parent.select(selected, "system") is original
    child = backend([replacement] if renumbered else [])
    monkeypatch.setattr(capture, "SoundCardBackend", lambda: child)
    monkeypatch.setattr(capture.signal, "signal", lambda *args: None)
    updates, errors = Queue(maxsize=1), Queue(maxsize=1)
    capture._worker(selected, "system", 48000, updates, errors, Event(), raw=True)
    assert "Device ID not found" in errors.get_nowait()
    assert updates.empty()
    assert not recorder_calls


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


def test_macos_level_check_binds_identity_before_spawning(monkeypatch):
    selection = InputIdentity('101', 'synthetic-uid')
    calls, child_args = [], []
    class FakeQueue(Queue):
        def close(self):
            pass
        def cancel_join_thread(self):
            pass
    class Process:
        def __init__(self, **kwargs):
            child_args.append(kwargs['args'])
        def start(self):
            pass
        def join(self, **kwargs):
            pass
        def is_alive(self):
            return False
    def bind(device, source):
        assert (device, source) == ('101', 'system')
        calls.append('bound')
        return selection
    monkeypatch.setattr(capture.platform, 'system', lambda: 'Darwin')
    monkeypatch.setattr(capture, 'SoundCardBackend', lambda: SimpleNamespace(bind=bind))
    # Binding occurs before queue/process creation.
    def queues(**kwargs):
        queue = FakeQueue(**kwargs)
        if len(calls) == 1:
            calls.append('updates')
        else:
            queue.put('synthetic stop')
        return queue
    monkeypatch.setattr(capture.mp, 'get_context', lambda mode: SimpleNamespace(
        Queue=queues, Event=Event, Process=Process))
    with pytest.raises(AudioError, match='synthetic stop'):
        next(capture.capture_levels('101', 'system', 48000))
    assert child_args[0][0] == selection
    assert calls == ['bound', 'updates']


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
    monkeypatch.setattr(capture, 'SoundCardBackend', lambda: SimpleNamespace(bind=lambda device, source: device))
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
