from contextlib import nullcontext
from queue import Queue
from types import SimpleNamespace

import pytest

from liltide.audio import AudioError
from liltide import provider
from liltide.provider import AzureProvider, Caption, CloudConfig


class Signal:
    def __init__(self):
        self.handlers = []
    def connect(self, handler):
        self.handlers.append(handler)
    def emit(self, event):
        for handler in self.handlers:
            handler(event)


@pytest.mark.parametrize("authentication_failure", [False, True])
def test_sdk_worker_configuration_callbacks_and_drain(monkeypatch, authentication_failure):
    # Importing SDK code is local. All constructors/operations below are fake.
    import azure.cognitiveservices.speech as sdk
    monkeypatch.setattr(provider.signal, "signal", lambda *args: None)
    state = {}
    class Settings:
        def __init__(self, **kwargs):
            state['settings'] = self
            self.languages = []
        def add_target_language(self, language):
            self.languages.append(language)
    class Recognizer:
        def __init__(self, **kwargs):
            state['recognizer'] = self
            self.recognizing = Signal()
            self.recognized = Signal()
            self.canceled = Signal()
            self.session_stopped = Signal()
        def start_continuous_recognition_async(self):
            def get():
                if authentication_failure:
                    self.canceled.emit(SimpleNamespace(reason=sdk.CancellationReason.Error,
                        error_code=sdk.CancellationErrorCode.AuthenticationFailure))
            return SimpleNamespace(get=get)
        def stop_continuous_recognition_async(self):
            state['stopped'] = True
            return SimpleNamespace(get=lambda: None)
    class Stream:
        def __init__(self, **kwargs):
            pass
        def write(self, chunk):
            state['chunk'] = chunk
            result = SimpleNamespace(offset=10000000, duration=2000000,
                text='Cześć', translations={'en': 'Hello'}, reason=sdk.ResultReason.TranslatedSpeech)
            r = state['recognizer']
            r.recognizing.emit(SimpleNamespace(result=result))
            r.recognized.emit(SimpleNamespace(result=result))
        def close(self):
            state['recognizer'].session_stopped.emit(None)
    monkeypatch.setattr(sdk.translation, "SpeechTranslationConfig", Settings)
    monkeypatch.setattr(sdk.translation, "TranslationRecognizer", Recognizer)
    monkeypatch.setattr(sdk.audio, "PushAudioInputStream", Stream)
    def format(**kwargs):
        state['format'] = kwargs
        return None
    monkeypatch.setattr(sdk.audio, "AudioStreamFormat", format)
    monkeypatch.setattr(sdk.audio, "AudioConfig", lambda **kwargs: None)
    monkeypatch.setattr(sdk, "Connection", SimpleNamespace(
        from_recognizer=lambda r: SimpleNamespace(disconnected=Signal())))
    incoming, events, errors = Queue(), Queue(), Queue()
    incoming.put(b'\x00\x00' * 100)
    incoming.put(None)
    ack = SimpleNamespace(value=0, get_lock=lambda: nullcontext())
    provider._azure_worker(CloudConfig('fake-not-a-real-key', 'westeurope'), incoming, events, errors, ack)
    assert state['settings'].speech_recognition_language == 'pl-PL'
    assert state['settings'].languages == ['en']
    assert state['format'] == dict(samples_per_second=16000, bits_per_sample=16, channels=1)
    if authentication_failure:
        assert 'authentication' in errors.get_nowait()
        assert ack.value == 0
    else:
        result = []
        while not events.empty():
            result.append(events.get_nowait())
        assert result[0] == 'ready' and result[-1] == 'stopped'
        assert [e.final for e in result if isinstance(e, Caption)] == [False, True]
        assert ack.value == 200 and state['stopped'] and errors.empty()


def test_provider_backlog_is_bounded_before_sdk_write():
    p = AzureProvider.__new__(AzureProvider)
    p.sent = 32000
    p.acknowledged = SimpleNamespace(value=0)
    p.incoming = Queue(maxsize=10)
    with pytest.raises(AudioError, match="backlog"):
        p.write(b'\x00\x00')
    assert p.incoming.empty()


def test_provider_queue_full_is_a_reported_gap():
    p = AzureProvider.__new__(AzureProvider)
    p.sent = 0
    p.acknowledged = SimpleNamespace(value=0)
    p.incoming = Queue(maxsize=1)
    p.write(b'\x00\x00')
    with pytest.raises(AudioError, match="Audio gap"):
        p.write(b'\x00\x00')


def test_start_timeout_does_not_wait_indefinitely(monkeypatch):
    p = AzureProvider.__new__(AzureProvider)
    p.process = SimpleNamespace(start=lambda: None)
    p.poll = lambda: []
    ticks = iter([0, 0, 16])
    monkeypatch.setattr(provider.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(provider.time, "sleep", lambda seconds: None)
    with pytest.raises(AudioError, match="startup timed out"):
        p.start()


def test_finish_timeout_always_aborts_worker(monkeypatch):
    p = AzureProvider.__new__(AzureProvider)
    p.started = True
    p.incoming = Queue()
    p.poll = lambda: []
    aborted = []
    p.abort = lambda: aborted.append(True)
    ticks = iter([0, 0, 4])
    monkeypatch.setattr(provider.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(provider.time, "sleep", lambda seconds: None)
    with pytest.raises(AudioError, match="finalization exceeded"):
        list(p.finish())
    assert aborted
