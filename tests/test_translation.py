from datetime import timedelta
import io
from pathlib import Path
from types import SimpleNamespace
import wave

import numpy as np
import pytest
from rich.console import Console
from typer.testing import CliRunner

from liltide.audio import AudioError
from liltide.cli import app
from liltide.pcm import PCMEncoder
from liltide.provider import Caption, CloudConfig, caption_from_result, cancellation_message
from liltide.session import TranslationSession
from liltide.sources import WaveSource
from liltide.terminal import CaptionRenderer, timestamp


def write_wav(path, *, width=2, channels=2, rate=44100):
    with wave.open(str(path), "wb") as f:
        f.setnchannels(channels)
        f.setsampwidth(width)
        f.setframerate(rate)
        f.writeframes(bytes(rate * width * channels // 2))


@pytest.mark.parametrize("rate", [16000, 44100, 48000])
def test_pcm_stream_matches_one_pass_and_quantizes_correctly(rate):
    samples = np.full((rate, 2), .25, dtype=np.float32)
    split = PCMEncoder(rate)
    streamed = b"".join(split.encode(chunk) for chunk in np.array_split(samples, 10)) + split.flush()
    whole = PCMEncoder(rate)
    assert streamed == whole.encode(samples, last=True)
    assert len(streamed) == 32000
    assert np.median(np.frombuffer(streamed, "<i2")) == pytest.approx(8192, abs=1)


def test_pcm_invalid_input_and_clipping():
    with pytest.raises(AudioError):
        PCMEncoder(48000).encode([[np.nan, 0]])
    data = PCMEncoder(16000).encode(np.full((16000, 2), -2), last=True)
    assert np.frombuffer(data, "<i2").min() == -32768


def test_wave_pacing_cursor_resume_and_validation(tmp_path, monkeypatch):
    import liltide.sources as sources
    now = [0.0]
    monkeypatch.setattr(sources.time, "monotonic", lambda: now[0])
    path = tmp_path / "synthetic.wav"
    write_wav(path)
    source = WaveSource(path)
    assert source.read().shape == (4410, 2)
    assert source.read() is None
    now[0] = 20
    cursor = source.file.tell()
    source.resume()
    assert source.file.tell() == cursor
    assert source.read().shape == (4410, 2)
    source.close()
    assert source.file.closed if hasattr(source.file, "closed") else source.file._file is None
    write_wav(path, width=1)
    with pytest.raises(AudioError, match="PCM16"):
        WaveSource(path)


def test_confirmation_and_credentials_redacted(monkeypatch):
    monkeypatch.setenv("AZURE_SPEECH_KEY", "synthetic-private-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "westeurope")
    with pytest.raises(AudioError, match="--confirm-f0"):
        CloudConfig.from_environment()
    assert "synthetic-private-key" not in repr(CloudConfig.from_environment(True))
    monkeypatch.delenv("AZURE_SPEECH_KEY")
    with pytest.raises(AudioError, match="locally"):
        CloudConfig.from_environment(True)


@pytest.mark.parametrize("duration", [3000000, timedelta(milliseconds=300)])
def test_result_time_and_unicode(duration):
    result = SimpleNamespace(offset=10000000, duration=duration, text="Zażółć gęślą jaźń", translations={"en": "A synthetic translation"})
    event = caption_from_result(result, True)
    assert event.start_ms == 1000 and event.end_ms == 1300
    assert event.polish == result.text and event.final


def test_missing_translation_is_not_invented():
    result = SimpleNamespace(offset=0, duration=0, text="Polski", translations={})
    assert caption_from_result(result, True).english is None


def test_cancellation_does_not_mislabel_unknown_failure():
    assert "quota exhaustion is not confirmed" in cancellation_message("Unknown")
    assert "No paid fallback" in cancellation_message("TooManyRequests")
    assert "authentication" in cancellation_message("AuthenticationFailure")


def test_renderer_noninteractive_final_only_plain_unicode():
    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=False)
    event = Caption("1", 1234, 2000, "Zażółć [red]", "Hello", False)
    with CaptionRenderer(console, "bilingual") as render:
        render.caption(event)
        assert not buffer.getvalue()
        render.caption(Caption(**{**event.__dict__, "final": True}))
    assert "Zażółć [red]" in buffer.getvalue()
    assert "[00:00:01.234] [final]" in buffer.getvalue()
    assert "\x1b" not in buffer.getvalue()
    assert timestamp(3661002) == "01:01:01.002"


class FakeSource:
    rate = 16000
    def __init__(self):
        self.reads = 0
        self.closed = False
        self.resumes = 0
    def read(self):
        self.reads += 1
        if self.reads > 1:
            raise StopIteration
        return np.zeros((1600, 2), np.float32)
    def close(self):
        self.closed = True
    def resume(self):
        self.resumes += 1


class FakeProvider:
    def __init__(self):
        self.writes = []
        self.aborted = False
    def start(self):
        pass
    def poll(self):
        return []
    def write(self, pcm):
        self.writes.append(pcm)
    def finish(self):
        event = Caption("0", 0, 100, "Cześć", "Hello", True)
        yield event
        yield event  # Deduplicate callback delivery.
    def abort(self):
        self.aborted = True


def test_session_eof_flushes_and_keeps_final_once():
    source, provider = FakeSource(), FakeProvider()
    events, statuses = [], []
    session = TranslationSession(lambda: source, lambda: provider, events.append, statuses.append)
    session.run()
    assert source.closed and provider.aborted
    assert len(events) == len(session.finalized) == 1
    assert events[0].polish == "Cześć"
    assert sum(map(len, provider.writes)) == 3200


def test_pause_reopens_live_source_but_retains_finalized_text():
    sources, providers = [], []
    def source_factory():
        source = FakeSource()
        sources.append(source)
        return source
    def provider_factory():
        provider = FakeProvider()
        providers.append(provider)
        return provider
    keys = iter(["pause", "pause", None, None])
    session = TranslationSession(source_factory, provider_factory, lambda e: None, lambda s: None,
                                 lambda: next(keys, None))
    session.run()
    assert len(sources) == len(providers) == 2
    assert all(source.closed for source in sources)
    assert all(provider.aborted for provider in providers)
    assert len(session.finalized) == 2


def test_file_pause_keeps_cursor_and_source_instance():
    source = FakeSource()
    providers = []
    def provider_factory():
        provider = FakeProvider()
        providers.append(provider)
        return provider
    keys = iter([None, "pause", "pause", None])
    session = TranslationSession(lambda: source, provider_factory, lambda e: None, lambda s: None,
                                 lambda: next(keys, None), file_input=True)
    session.run()
    assert source.reads == 2 and source.resumes == 2 and source.closed
    assert len(providers) == 2


def test_startup_failure_cleans_both_sources_and_provider():
    source, provider = FakeSource(), FakeProvider()
    def bad_start():
        raise AudioError("Synthetic failure")
    provider.start = bad_start
    session = TranslationSession(lambda: source, lambda: provider, lambda e: None, lambda s: None)
    with pytest.raises(AudioError, match="Synthetic"):
        session.run()
    assert provider.aborted and source.closed


@pytest.mark.parametrize("args,expected", [
    (["run", "--device", "fake"], "--confirm-f0"),
    (["run", "--check-audio", "--device", "fake", "--confirm-f0"], "incompatible"),
    (["run", "--source", "file", "--device", "fake"], "requires --file"),
    (["run", "--file", "missing.wav"], "requires --source file"),
])
def test_cloud_cli_preflight_without_network(args, expected):
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 1
    assert expected in result.output


def test_full_file_cli_with_fake_provider_no_exports(tmp_path, monkeypatch):
    from liltide import provider as module
    path = tmp_path / "synthetic.wav"
    write_wav(path, rate=16000)
    monkeypatch.setenv("AZURE_SPEECH_KEY", "synthetic-private-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "westeurope")
    monkeypatch.setattr(module, "AzureProvider", lambda config: FakeProvider())
    result = CliRunner().invoke(app, ["run", "--source", "file", "--file", str(path), "--confirm-f0", "--view", "english"])
    assert result.exit_code == 0, result.output
    assert "EN: Hello" in result.output and "PL:" not in result.output
    assert "synthetic-private-key" not in result.output
    assert list(tmp_path.iterdir()) == [path]
