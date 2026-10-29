import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import wave

import pytest
from typer.testing import CliRunner

from liltide.audio import AudioError
from liltide.cli import app
from liltide.exports import TranscriptExports
from liltide.provider import Caption
from liltide.session import TranslationSession


def caption(final=True, english="Hello"):
    return Caption("0", 1234, 2345, "Zażółć gęślą jaźń\nDruga linia", english, final)


def test_default_no_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with TranscriptExports() as exports:
        exports.caption(caption())
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("kind", ["text", "jsonl", "both"])
def test_final_only_unicode_and_flush_before_close(tmp_path, kind):
    text, data = tmp_path / "session.txt", tmp_path / "session.jsonl"
    with TranscriptExports(text if kind != "jsonl" else None, data if kind != "text" else None) as sink:
        sink.caption(caption(False))
        assert all(path.stat().st_size == 0 for path in tmp_path.iterdir())
        sink.caption(caption(english=None))
        if kind != "jsonl":
            contents = text.read_text(encoding="utf-8")
            assert "[00:00:01.234 --> 00:00:02.345] [final]" in contents
            assert "Zażółć gęślą jaźń" in contents and "translation unavailable" in contents
        if kind != "text":
            lines = data.read_text(encoding="utf-8").splitlines()
            assert len(lines) == 1  # Embedded speech newlines stay inside one JSON record.
            record = json.loads(lines[0])
            assert record == dict(type="segment", session_id=sink.session_id, segment_id="0",
                start_ms=1234, end_ms=2345, source_language="pl-PL", target_language="en",
                source_text=caption().polish, translation_text=None,
                arrival_ms=None, handled_ms=None, timing_source=None, dispatch_delay_ms=None,
                first_provisional_arrival_ms=None, provisional_to_final_ms=None, estimated_final_delay_ms=None)
            assert "Zażółć" in lines[0] and record["type"] == "segment"
        if os.name != "nt":
            assert all(path.stat().st_mode & 0o777 == 0o600 for path in tmp_path.iterdir())


def test_existing_second_destination_leaves_first_uncreated(tmp_path):
    text, data = tmp_path / "session.txt", tmp_path / "session.jsonl"
    data.write_text("keep me", encoding="utf-8")
    with pytest.raises(AudioError, match="already exists"):
        with TranscriptExports(text, data):
            pass
    assert not text.exists() and data.read_text() == "keep me"


def test_same_destination_and_missing_parent(tmp_path):
    path = tmp_path / "same"
    with pytest.raises(AudioError, match="different paths"):
        with TranscriptExports(path, tmp_path / "." / "same"):
            pass
    with pytest.raises(AudioError, match="parent directory"):
        with TranscriptExports(tmp_path / "missing" / "session.txt"):
            pass
    assert list(tmp_path.iterdir()) == []


def test_partial_open_failure_rolls_back_new_empty_file(tmp_path, monkeypatch):
    from liltide import exports as module
    real_open = os.open
    def fail_second(path, flags, mode):
        if Path(path).suffix == ".jsonl":
            raise PermissionError("synthetic denied")
        return real_open(path, flags, mode)
    monkeypatch.setattr(module.os, "open", fail_second)
    with pytest.raises(AudioError, match="Cannot create"):
        with TranscriptExports(tmp_path / "session.txt", tmp_path / "session.jsonl"):
            pass
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("operation", ["write", "flush", "fsync"])
def test_disk_errors_are_actionable(tmp_path, monkeypatch, operation):
    def fail(*args):
        raise OSError("synthetic disk failure")
    with TranscriptExports(tmp_path / "session.txt") as sink:
        file = sink.files[0][2]
        if operation == "fsync":
            monkeypatch.setattr(os, "fsync", fail)
        else:
            wrapper = SimpleNamespace(write=file.write, flush=file.flush, fileno=file.fileno, close=file.close)
            setattr(wrapper, operation, fail)
            sink.files[0] = ("text", tmp_path / "session.txt", wrapper)
        with pytest.raises(AudioError, match="Session stopped"):
            sink.caption(caption())


class Source:
    rate = 16000
    def __init__(self, interruption=None):
        self.closed = False
        self.interruption = interruption
    def resume(self):
        pass
    def close(self):
        self.closed = True
    def read(self):
        if self.interruption:
            raise self.interruption
        raise StopIteration


class Provider:
    def __init__(self):
        self.aborted = False
    def start(self):
        pass
    def poll(self):
        return [Caption("0", 0, 15000, "", "", True),
                Caption("0", 0, 15000, " \n", None, True),
                caption(False), caption(), caption()]
    def write(self, data):
        pass
    def finish(self):
        yield caption()  # A repeated final during shutdown must not be re-exported.
    def abort(self):
        self.aborted = True


@pytest.mark.parametrize("interruption", [None, KeyboardInterrupt(), AudioError("Synthetic disconnect")])
def test_final_survives_eof_ctrl_c_or_provider_failure(tmp_path, interruption):
    path = tmp_path / "session.jsonl"
    source, provider = Source(interruption), Provider()
    with TranscriptExports(jsonl_path=path) as sink:
        def displayed(event):
            if event.final:
                assert len(path.read_text(encoding="utf-8").splitlines()) == 1
        session = TranslationSession(lambda: source, lambda: provider, displayed, lambda msg: None,
                                     on_finalized=sink.caption)
        if isinstance(interruption, AudioError):
            with pytest.raises(AudioError, match="Synthetic disconnect"):
                session.run()
        else:
            session.run()
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1
    assert source.closed and provider.aborted


def test_export_failure_stops_capture_and_aborts_provider():
    source, provider = Source(), Provider()
    def fail(event):
        raise AudioError("Synthetic export failure")
    session = TranslationSession(lambda: source, lambda: provider, lambda e: None, lambda m: None,
                                 on_finalized=fail)
    with pytest.raises(AudioError, match="export failure"):
        session.run()
    assert source.closed and provider.aborted


def test_export_failure_during_final_drain_still_releases_resources():
    source, provider = Source(), Provider()
    provider.poll = lambda: []
    def fail(event):
        raise AudioError("Synthetic drain export failure")
    session = TranslationSession(lambda: source, lambda: provider, lambda e: None, lambda m: None,
                                 on_finalized=fail)
    with pytest.raises(AudioError, match="drain export failure"):
        session.run()
    assert source.closed and provider.aborted


def test_pause_resume_keeps_one_export_session_without_reusing_segment_ids(tmp_path):
    path = tmp_path / "session.jsonl"
    keys = iter(["pause", "pause", None])
    with TranscriptExports(jsonl_path=path) as sink:
        session = TranslationSession(Source, Provider, lambda e: None, lambda m: None,
            lambda: next(keys, None), on_finalized=sink.caption)
        session.run()
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 2
    assert len({r["session_id"] for r in records}) == 1
    assert len({r["segment_id"] for r in records}) == 2


def test_persisted_record_survives_abrupt_process_exit(tmp_path):
    path = tmp_path / "session.jsonl"
    code = """
import os, sys
from liltide.exports import TranscriptExports
from liltide.provider import Caption
with TranscriptExports(jsonl_path=sys.argv[1]) as sink:
    sink.caption(Caption('0', 0, 100, 'Cześć', 'Hello', True))
    os._exit(7)
"""
    result = subprocess.run([sys.executable, "-c", code, str(path)], capture_output=True, timeout=10)
    assert result.returncode == 7
    assert json.loads(path.read_text(encoding="utf-8"))["source_text"] == "Cześć"


@pytest.fixture
def cloud_env(monkeypatch):
    monkeypatch.setenv("AZURE_SPEECH_KEY", "synthetic-not-a-real-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "westeurope")


def test_cli_existing_export_fails_before_source_or_cloud_start(tmp_path, monkeypatch, cloud_env):
    from liltide import provider as module
    def forbidden(*args):
        raise AssertionError("Provider must not be initialized")
    monkeypatch.setattr(module, "AzureProvider", forbidden)
    path = tmp_path / "exists.txt"
    path.write_text("keep me")
    result = CliRunner().invoke(app, ["run", "--source", "file", "--file", "unused.wav",
        "--confirm-f0", "--export-text", str(path)])
    assert result.exit_code == 1 and "already exists" in result.output
    assert path.read_text() == "keep me"


def test_cli_exports_both_languages_even_in_english_view(tmp_path, monkeypatch, cloud_env):
    from liltide import provider as module
    monkeypatch.setattr(module, "AzureProvider", lambda config: Provider())
    audio = tmp_path / "synthetic.wav"
    with wave.open(str(audio), "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(16000)
        file.writeframes(b"")
    text, data = tmp_path / "session.txt", tmp_path / "session.jsonl"
    result = CliRunner().invoke(app, ["run", "--source", "file", "--file", str(audio),
        "--confirm-f0", "--view", "english", "--export-text", str(text), "--export-jsonl", str(data)])
    assert result.exit_code == 0, result.output
    assert "PL:" not in result.output
    assert "Zażółć" in text.read_text(encoding="utf-8")
    records = [json.loads(line) for line in data.read_text(encoding="utf-8").splitlines()]
    assert [r['type'] for r in records] == ['session', 'segment']


def test_level_check_rejects_exports_without_creating_files(tmp_path):
    path = tmp_path / "session.txt"
    result = CliRunner().invoke(app, ["run", "--check-audio", "--device", "fake", "--export-text", str(path)])
    assert result.exit_code == 1 and "incompatible" in result.output
    assert not path.exists()


def test_exporter_rejects_blank_finals_even_without_session_filter(tmp_path):
    text, data = tmp_path / "session.txt", tmp_path / "session.jsonl"
    with TranscriptExports(text, data) as sink:
        sink.caption(Caption("0", 0, 15000, "", "", True))
        sink.caption(Caption("1", 0, 15000, " \n", None, True))
        assert text.read_bytes() == data.read_bytes() == b""
