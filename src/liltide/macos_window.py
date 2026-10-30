"""Small AppKit bridge for the optional macOS floating caption window."""

import ctypes as ct
from functools import lru_cache
import platform
import sys
from types import SimpleNamespace

CAN_JOIN_ALL_SPACES = 1 << 0
MOVE_TO_ACTIVE_SPACE = 1 << 1
FULLSCREEN_PRIMARY = 1 << 7
FULLSCREEN_AUXILIARY = 1 << 8
FULLSCREEN_NONE = 1 << 9
PRIMARY = 1 << 16
AUXILIARY = 1 << 17
CAN_JOIN_ALL_APPLICATIONS = 1 << 18


@lru_cache(maxsize=1)
def _runtime():
    objc = ct.CDLL('/usr/lib/libobjc.A.dylib')
    objc.sel_registerName.argtypes = [ct.c_char_p]
    objc.sel_registerName.restype = ct.c_void_p
    address = ct.cast(objc.objc_msgSend, ct.c_void_p).value
    # Typed signatures are essential on both arm64 and x86_64. These methods
    # return only object pointers / NSUInteger, never structs or floats.
    return SimpleNamespace(
        library=objc,
        selector=objc.sel_registerName,
        object=ct.CFUNCTYPE(ct.c_void_p, ct.c_void_p, ct.c_void_p)(address),
        integer=ct.CFUNCTYPE(ct.c_ulong, ct.c_void_p, ct.c_void_p)(address),
        set_integer=ct.CFUNCTYPE(None, ct.c_void_p, ct.c_void_p, ct.c_ulong)(address),
    )


def enable_fullscreen_panel(view_id):
    """Configure Qt's borrowed NSView/NSWindow on the GUI thread; retain neither."""
    if sys.platform != 'darwin' or not view_id:
        return False
    runtime = _runtime()
    window = runtime.object(int(view_id), runtime.selector(b'window'))
    if not window:
        return False
    getter = runtime.selector(b'collectionBehavior')
    original = runtime.integer(window, getter)
    removed = MOVE_TO_ACTIVE_SPACE | FULLSCREEN_PRIMARY | FULLSCREEN_NONE
    required = CAN_JOIN_ALL_SPACES | FULLSCREEN_AUXILIARY
    # These three newer behaviors are mutually exclusive (macOS 13+).
    if int(platform.mac_ver()[0].split('.')[0]) >= 13:
        removed |= PRIMARY | AUXILIARY
        required |= CAN_JOIN_ALL_APPLICATIONS
    desired = (original & ~removed) | required
    runtime.set_integer(window, runtime.selector(b'setCollectionBehavior:'), desired)
    actual = runtime.integer(window, getter)
    return actual & required == required and not actual & removed
