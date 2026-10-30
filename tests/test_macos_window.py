from types import SimpleNamespace

import pytest

from liltide import macos_window as native


@pytest.mark.parametrize('major', [12, 13, 27])
def test_window_policy_preserves_unrelated_flags_and_removes_conflicts(monkeypatch, major):
    monkeypatch.setattr(native.sys, 'platform', 'darwin')
    monkeypatch.setattr(native.platform, 'mac_ver', lambda: (f'{major}.0', (), ''))
    unrelated = (1 << 3) | (1 << 6)
    original = unrelated | native.MOVE_TO_ACTIVE_SPACE | native.FULLSCREEN_PRIMARY | native.FULLSCREEN_NONE
    if major >= 13:
        original |= native.PRIMARY | native.AUXILIARY
    values = [original]
    def get_object(view, selector):
        assert view == 123 and selector == b'window'
        return 456
    def get_integer(window, selector):
        assert window == 456 and selector == b'collectionBehavior'
        return values[-1]
    def set_integer(window, selector, value):
        assert window == 456 and selector == b'setCollectionBehavior:'
        values.append(value)
    monkeypatch.setattr(native, '_runtime', lambda: SimpleNamespace(
        selector=lambda name:name, object=get_object, integer=get_integer, set_integer=set_integer))
    assert native.enable_fullscreen_panel(123)
    expected = unrelated | native.CAN_JOIN_ALL_SPACES | native.FULLSCREEN_AUXILIARY
    if major >= 13:
        expected |= native.CAN_JOIN_ALL_APPLICATIONS
    assert values[-1] == expected


def test_non_macos_and_null_handle_never_load_objc(monkeypatch):
    monkeypatch.setattr(native, '_runtime', lambda: pytest.fail('Native runtime must not load'))
    monkeypatch.setattr(native.sys, 'platform', 'linux')
    assert not native.enable_fullscreen_panel(123)
    monkeypatch.setattr(native.sys, 'platform', 'darwin')
    assert not native.enable_fullscreen_panel(0)


def test_missing_native_window_is_safe(monkeypatch):
    monkeypatch.setattr(native.sys, 'platform', 'darwin')
    monkeypatch.setattr(native, '_runtime', lambda: SimpleNamespace(
        selector=lambda name:name, object=lambda *args:None))
    assert not native.enable_fullscreen_panel(123)


def test_rejected_policy_is_not_reported_as_enabled(monkeypatch):
    monkeypatch.setattr(native.sys, 'platform', 'darwin')
    monkeypatch.setattr(native.platform, 'mac_ver', lambda: ('27.0', (), ''))
    monkeypatch.setattr(native, '_runtime', lambda: SimpleNamespace(
        selector=lambda name:name, object=lambda *args:456,
        integer=lambda *args:0, set_integer=lambda *args:None))
    assert not native.enable_fullscreen_panel(123)
