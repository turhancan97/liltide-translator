from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from liltide import cli
from liltide.audio import AudioError, Device
from liltide.capture import Levels

runner = CliRunner()


def test_version():
    result = runner.invoke(cli.app, ["--version"])
    assert result.exit_code == 0
    assert "Liltide 0.1.0.dev0" in result.output


@pytest.mark.parametrize("args", [[], ["--help"], ["devices", "--help"], ["run", "--help"], ["doctor", "--help"]])
def test_help_never_initializes_audio(monkeypatch, args):
    def forbidden():
        raise AssertionError("help must not touch audio")
    monkeypatch.setattr(cli, "SoundCardBackend", forbidden)
    result = runner.invoke(cli.app, args)
    assert result.exit_code in (0, 2)  # no-argument usage exits 2
    assert "Usage" in result.output


@pytest.mark.parametrize("args,message", [
    (["run"], "--device is required"),
    (["run", "--check-audio"], "--device is required"),
    (["doctor", "--cloud"], "not implemented"),
    (["run", "--check-audio", "--device", "x", "--duration", "-1"], "Invalid value"),
    (["run", "--check-audio", "--device", "x", "--source", "file"], "requires --file"),
])
def test_invalid_requests_never_capture(monkeypatch, args, message):
    def forbidden(*a, **kw):
        raise AssertionError("invalid request must not capture")
    monkeypatch.setattr(cli, "capture_levels", forbidden)
    result = runner.invoke(cli.app, args)
    assert result.exit_code != 0
    assert message in result.output


def test_devices_treat_names_as_text(monkeypatch):
    monkeypatch.setattr(cli, "SoundCardBackend", lambda: SimpleNamespace(
        system="Darwin", devices=lambda: [Device("42", "[red]Synthetic[/red]", 2, "routed input")]))
    result = runner.invoke(cli.app, ["devices"], env={"NO_COLOR": "1"}, terminal_width=160)
    assert result.exit_code == 0
    assert "[red]Synthetic[/red]" in result.output
    assert "cannot be classified" in result.output
    assert "\x1b" not in result.output


def test_doctor_failure_actionable(monkeypatch):
    def unavailable():
        raise AudioError("Synthetic backend unavailable; check permissions")
    monkeypatch.setattr(cli, "SoundCardBackend", unavailable)
    result = runner.invoke(cli.app, ["doctor"])
    assert result.exit_code == 1
    assert "check permissions" in result.output
    assert "Traceback" not in result.output


def test_meter_closes_generator_on_ctrl_c(monkeypatch, tmp_path):
    closed = []
    def stream(*args):
        try:
            yield Levels(-6, -3, False)
            raise KeyboardInterrupt
        finally:
            closed.append(True)
    monkeypatch.setattr(cli, "capture_levels", stream)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli.app, ["run", "--check-audio", "--device", "fake"], env={"NO_COLOR": "1"})
    assert result.exit_code == 0
    assert "SIGNAL" in result.output and "Stopped" in result.output
    assert closed and not list(tmp_path.iterdir())
    assert "\x1b" not in result.output


def test_silent_meter_renders_without_overflow(monkeypatch):
    def silence(*args):
        yield Levels(-float("inf"), -float("inf"), False)
    monkeypatch.setattr(cli, "capture_levels", silence)
    result = runner.invoke(cli.app, ["run", "--check-audio", "--device", "fake"])
    assert result.exit_code == 0
    assert "SILENCE/LOW" in result.output
    assert "Finished" in result.output
