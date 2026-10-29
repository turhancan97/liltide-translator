"""Read-only CoreAudio identity lookup; loaded only on macOS."""

import ctypes as ct
from functools import lru_cache


class PropertyAddress(ct.Structure):
    _fields_ = [("selector", ct.c_uint32), ("scope", ct.c_uint32), ("element", ct.c_uint32)]


@lru_cache(maxsize=1)
def _libraries():
    ca = ct.CDLL('/System/Library/Frameworks/CoreAudio.framework/CoreAudio')
    cf = ct.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
    ca.AudioObjectGetPropertyData.argtypes = [ct.c_uint32, ct.POINTER(PropertyAddress),
                                            ct.c_uint32, ct.c_void_p,
                                            ct.POINTER(ct.c_uint32), ct.c_void_p]
    ca.AudioObjectGetPropertyData.restype = ct.c_int32
    cf.CFStringGetLength.argtypes = [ct.c_void_p]
    cf.CFStringGetLength.restype = ct.c_long
    cf.CFStringGetCString.argtypes = [ct.c_void_p, ct.c_void_p, ct.c_long, ct.c_uint32]
    cf.CFStringGetCString.restype = ct.c_ubyte
    cf.CFRelease.argtypes = [ct.c_void_p]
    cf.CFRelease.restype = None
    return ca, cf


def device_uid(device_id):
    """Return an opaque UID, releasing the owned CFString on every path."""
    numeric = int(device_id)
    if not 0 < numeric <= 0xFFFFFFFF:
        raise ValueError('Invalid CoreAudio object ID')
    ca, cf = _libraries()
    address = PropertyAddress(int.from_bytes(b'uid ', 'big'), int.from_bytes(b'glob', 'big'), 0)
    value = ct.c_void_p()
    size = ct.c_uint32(ct.sizeof(value))
    status = ca.AudioObjectGetPropertyData(numeric, ct.byref(address), 0, None,
                                         ct.byref(size), ct.byref(value))
    if status != 0 or not value.value:
        raise RuntimeError('CoreAudio identity unavailable')
    try:
        if size.value != ct.sizeof(value):
            raise RuntimeError('Invalid CoreAudio identity size')
        length = cf.CFStringGetLength(value)
        if length < 1:
            raise RuntimeError('Empty CoreAudio identity')
        buffer = ct.create_string_buffer(length * 4 + 1)
        if not cf.CFStringGetCString(value, buffer, len(buffer), 0x08000100):
            raise RuntimeError('Cannot decode CoreAudio identity')
        return buffer.value.decode('utf-8')
    finally:
        cf.CFRelease(value)
