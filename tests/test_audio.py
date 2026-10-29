from types import SimpleNamespace

import numpy as np
import pytest

from liltide.audio import AudioError, InputIdentity, SoundCardBackend
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


def test_macos_virtual_input_is_not_guessed_by_name(monkeypatch):
    source = mic(id=123)
    b = backend("Darwin", [source])
    monkeypatch.setattr(b, '_uid', lambda mic: 'synthetic-uid')
    assert b.devices()[0].kind == "routed input"
    assert b.select("123", "system") is source


def test_windows_mono_backend_limitation():
    with pytest.raises(AudioError, match="Mono WASAPI"):
        backend("Windows", [mic(channels=1)]).select("exact-id", "microphone")


def test_persistent_identity_survives_renumbering_without_name_fallback(monkeypatch):
    original = mic(id=101)
    b = backend('Darwin', [original])
    monkeypatch.setattr(b, '_uid', lambda item: item.uid)
    original.uid = 'synthetic-uid'
    selection = b.devices()[0].selection
    assert selection == b.bind('101', 'system')
    replacement = mic(id=202)
    replacement.uid = original.uid
    reused_id = mic(id=101)
    reused_id.uid = 'different-uid'
    b.sc.all_microphones = lambda **kw: [reused_id, replacement]
    assert b.select(selection, 'system') is replacement
    assert b.bind(selection, 'system') is selection
    assert 'synthetic-uid' not in repr(selection)
    import pickle
    assert pickle.loads(pickle.dumps(selection)) == selection


@pytest.mark.parametrize('failure', ['missing', 'ambiguous', 'unavailable'])
def test_identity_failures_are_closed_and_do_not_expose_identifiers(monkeypatch, failure):
    source = mic(id=101)
    source.uid = 'private-synthetic-uid'
    devices = [] if failure == 'missing' else [source] * (2 if failure == 'ambiguous' else 1)
    b = backend('Darwin', devices)
    def uid(item):
        if failure == 'unavailable':
            raise RuntimeError('private native text')
        return item.uid
    monkeypatch.setattr(b, '_uid', uid)
    with pytest.raises(AudioError, match=f'identity.*{failure}') as error:
        b.select(InputIdentity('private-numeric-id', source.uid), 'system')
    message = str(error.value)
    assert f'inputs={len(devices)}' in message
    assert 'previous_numeric_id_present=no' in message
    assert 'No fallback' in message
    assert 'private' not in message


def test_persistent_identity_cannot_cross_backend_types():
    with pytest.raises(AudioError, match='invalid for this backend'):
        backend('Linux', []).select(InputIdentity('101', 'synthetic-uid'), 'system')


def test_reused_numeric_id_does_not_replace_missing_identity(monkeypatch):
    b = backend('Darwin', [mic(id=101)])
    monkeypatch.setattr(b, '_uid', lambda item: 'different-uid')
    with pytest.raises(AudioError, match='missing.*previous_numeric_id_present=yes'):
        b.select(InputIdentity('101', 'original-uid'), 'system')


def test_non_macos_binding_keeps_exact_endpoint_without_uid_lookup(monkeypatch):
    b = backend('Linux', [mic(loopback=True)])
    monkeypatch.setattr(b, '_uid', lambda item: pytest.fail('UID must not be used here'))
    assert b.bind('exact-id', 'system') == 'exact-id'


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
