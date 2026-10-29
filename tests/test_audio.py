from types import SimpleNamespace

import numpy as np
import pytest

from liltide.audio import AudioError, SoundCardBackend
from liltide.capture import measure_levels


def backend(system, devices):
    instance = SoundCardBackend.__new__(SoundCardBackend)
    instance.system = system
    instance.sc = SimpleNamespace(all_microphones=lambda **kwargs: devices)
    return instance


def mic(id="exact-id", loopback=False, channels=2):
    return SimpleNamespace(id=id, name="Synthetic source", channels=channels, isloopback=loopback)


@pytest.mark.parametrize("system", ["Windows", "Linux"])
def test_source_types_and_exact_selection(system):
    source = mic(loopback=True)
    b = backend(system, [source, mic(id="other")])
    assert [d.kind for d in b.devices()] == ["system", "microphone"]
    assert b.select("exact-id", "system") is source
    with pytest.raises(AudioError, match="not found"):
        b.select("exact", "system")
    with pytest.raises(AudioError, match="No fallback"):
        b.select("other", "system")


def test_macos_virtual_input_is_not_guessed_by_name():
    source = mic(id=123)
    b = backend("Darwin", [source])
    assert b.devices()[0].kind == "routed input"
    assert b.select("123", "system") is source


def test_windows_mono_backend_limitation():
    with pytest.raises(AudioError, match="Mono WASAPI"):
        backend("Windows", [mic(channels=1)]).select("exact-id", "microphone")


def test_levels_silence_signal_and_clipping():
    assert measure_levels(np.zeros((100, 2))).rms_dbfs == -float("inf")
    # Stereo cancellation must not hide the level during capture diagnostics.
    result = measure_levels(np.tile([0.5, -0.5], (100, 1)))
    assert result.rms_dbfs == pytest.approx(-6.0206)
    assert result.peak_dbfs == pytest.approx(-6.0206)
    assert not result.clipping
    assert measure_levels(np.ones((100, 2))).clipping


@pytest.mark.parametrize("data", [np.empty((0, 2)), np.ones(2), [[np.nan]], [[np.inf]]])
def test_invalid_samples_are_errors(data):
    with pytest.raises(AudioError):
        measure_levels(data)
