import ctypes as ct
from types import SimpleNamespace

import pytest

from liltide import coreaudio_identity as identity


@pytest.mark.parametrize('failure', [None, 'property', 'decode', 'empty'])
def test_uid_native_boundary_releases_owned_string(monkeypatch, failure):
    released = []
    def get_property(device, address, qualifier_size, qualifier, size, value):
        assert device == 101
        prop = ct.cast(address, ct.POINTER(identity.PropertyAddress)).contents
        assert prop.selector == int.from_bytes(b'uid ', 'big')
        assert prop.scope == int.from_bytes(b'glob', 'big')
        if failure == 'property':
            return -1
        ct.cast(value, ct.POINTER(ct.c_void_p))[0] = 123
        return 0
    def decode(value, buffer, size, encoding):
        assert encoding == 0x08000100
        if failure == 'decode':
            return 0
        buffer.value = b'synthetic-uid'
        return 1
    ca = SimpleNamespace(AudioObjectGetPropertyData=get_property)
    cf = SimpleNamespace(CFStringGetLength=lambda value: 0 if failure == 'empty' else 13,
                         CFStringGetCString=decode, CFRelease=lambda value: released.append(value.value))
    monkeypatch.setattr(identity, '_libraries', lambda: (ca, cf))
    if failure:
        with pytest.raises(RuntimeError):
            identity.device_uid('101')
    else:
        assert identity.device_uid('101') == 'synthetic-uid'
    assert released == ([] if failure == 'property' else [123])


@pytest.mark.parametrize('value', ['invalid', '0', '-1', str(2**32)])
def test_invalid_object_ids_never_load_native_libraries(monkeypatch, value):
    def forbidden():
        pytest.fail('Invalid object IDs must fail before loading CoreAudio')
    monkeypatch.setattr(identity, '_libraries', forbidden)
    with pytest.raises(ValueError):
        identity.device_uid(value)
