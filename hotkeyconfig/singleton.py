"""One configurator window at a time.

Opening the configurator twice does not give two usable windows. WebView2 keeps
its data in a folder per user, and the second instance sits waiting for it: blank
window, and Windows marking it as "not responding". It looks exactly like a broken
app when all that happened is that it was opened twice. So the second one hands
the existing window back to the user and steps aside.

The lock is a named Windows mutex, which the system drops on its own if the
process dies, crash included. Off Windows there is nothing to guard against here.
"""

from __future__ import annotations

import ctypes
import logging
import sys

log = logging.getLogger("hotkeyconfig.singleton")

IS_WINDOWS = sys.platform == "win32"
# "Local\" keeps it inside the user session: two accounts logged into the same
# machine each get their own, which is what they would expect.
CONFIGURATOR = "Local\\hotkeyconfig-configurator"
# The listener has its own lock for a different reason: two of them running at once
# means every key press fires twice, and that is a bug that hides very well (it once
# opened three browser tabs from a single press).
LISTENER = "Local\\hotkeyconfig-listener"
ERROR_ALREADY_EXISTS = 183
SYNCHRONIZE = 0x00100000

_handles: dict[str, int] = {}   # se guardan para que el candado dure lo que el proceso


def _kernel32():
    lib = ctypes.WinDLL("kernel32", use_last_error=True)
    lib.CreateMutexW.restype = ctypes.c_void_p
    lib.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    lib.OpenMutexW.restype = ctypes.c_void_p
    lib.OpenMutexW.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_wchar_p]
    lib.CloseHandle.argtypes = [ctypes.c_void_p]
    return lib


def claim(name: str = CONFIGURATOR) -> bool:
    """Take the lock. True if we are the only one, False if somebody else has it.

    Anything unexpected answers True: failing to start would be a worse bug than
    starting twice.
    """
    if not IS_WINDOWS:
        return True
    try:
        lib = _kernel32()
        handle = lib.CreateMutexW(None, True, name)
        if not handle:
            return True
        _handles[name] = handle
        return ctypes.get_last_error() != ERROR_ALREADY_EXISTS
    except Exception:  # noqa: BLE001
        log.debug("could not take the lock %s", name, exc_info=True)
        return True


def taken(name: str) -> bool:
    """Whether somebody holds that lock right now, us included."""
    if not IS_WINDOWS:
        return False
    try:
        lib = _kernel32()
        handle = lib.OpenMutexW(SYNCHRONIZE, False, name)
        if handle:
            lib.CloseHandle(handle)
            return True
        return False
    except Exception:  # noqa: BLE001
        log.debug("could not check the lock %s", name, exc_info=True)
        return False
