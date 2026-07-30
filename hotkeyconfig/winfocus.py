"""Bringing the window we just opened to the front (Windows only).

Windows refuses ``SetForegroundWindow`` to a process that does not own the active
window, which is exactly our situation: the listener sits in the background while
the user works in another app. Two things are needed.

1. ``AllowSetForegroundWindow`` before launching, so the process we start is
   allowed to come forward by itself.
2. When the browser is already running it usually hands the URL to the existing
   instance and exits, so nothing ever asks for the foreground. In that case the
   window has to be found and raised here, attaching to the input queue of the
   active window, which is what lifts the block.

Everything degrades to a no-op off Windows and never raises: failing to focus a
window must not break the action that was just run.
"""

from __future__ import annotations

import ctypes
import logging
import os
import sys
import threading
import time

log = logging.getLogger("hotkeyconfig.winfocus")

IS_WINDOWS = sys.platform == "win32"

ASFW_ANY = -1
SW_RESTORE = 9
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
MOUSEEVENTF_MOVE = 0x0001

if IS_WINDOWS:
    from ctypes import wintypes

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    # Explicit prototypes: without them ctypes assumes a 32 bit int return and
    # truncates window handles on 64 bit Windows.
    _ENUM_PROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    _user32.EnumWindows.argtypes = [_ENUM_PROC, wintypes.LPARAM]
    _user32.EnumWindows.restype = wintypes.BOOL
    _user32.IsWindowVisible.argtypes = [wintypes.HWND]
    _user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    _user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    _user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    _user32.IsIconic.argtypes = [wintypes.HWND]
    _user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    _user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    _user32.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
    _user32.mouse_event.argtypes = [
        wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
    try:  # undocumented, so it is used only if this build of Windows exports it
        _user32.SwitchToThisWindow.argtypes = [wintypes.HWND, wintypes.BOOL]
    except AttributeError:  # pragma: no cover
        log.debug("SwitchToThisWindow not available")
    _kernel32.GetCurrentThreadId.restype = wintypes.DWORD
    _kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _kernel32.OpenProcess.restype = wintypes.HANDLE
    _kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def allow_foreground() -> None:
    """Let the next process we launch put itself in front. Call before launching."""
    if not IS_WINDOWS:
        return
    try:
        _user32.AllowSetForegroundWindow(ASFW_ANY)
    except Exception:  # noqa: BLE001 - focus is a nicety, never a failure
        log.debug("AllowSetForegroundWindow failed", exc_info=True)


def _image_name(pid: int) -> str:
    handle = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(520)
        size = wintypes.DWORD(len(buf))
        if _kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    finally:
        _kernel32.CloseHandle(handle)


def _windows_of(exe: str) -> list[int]:
    """Visible top level windows with a title that belong to that executable."""
    wanted = os.path.basename(exe).lower()
    found: list[int] = []

    def visit(hwnd, _param):
        if _user32.IsWindowVisible(hwnd) and _user32.GetWindowTextLengthW(hwnd):
            pid = wintypes.DWORD()
            _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if os.path.basename(_image_name(pid.value)).lower() == wanted:
                found.append(hwnd)
        return True

    _user32.EnumWindows(_ENUM_PROC(visit), 0)
    return found


def _attach_and_set(hwnd: int) -> None:
    """Ask for the foreground while borrowing the input queue of the active window."""
    active = _user32.GetForegroundWindow()
    ours = _kernel32.GetCurrentThreadId()
    theirs = _user32.GetWindowThreadProcessId(active, None) if active else 0
    attached = bool(theirs) and theirs != ours and bool(
        _user32.AttachThreadInput(theirs, ours, True))
    try:
        _user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            _user32.AttachThreadInput(theirs, ours, False)


def _nudge_and_set(hwnd: int) -> None:
    """Same, after a mouse move of zero pixels.

    Windows grants the foreground to whoever handled the last input event, so a
    null move makes it treat this as something the user just asked for. Measured
    on Windows 11: this is the only route that works from a background process.
    A zero pixel move is the least intrusive nudge there is, unlike the usual
    trick of faking an alt keypress, which pops open menus in the active app.
    """
    _user32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, None)
    _attach_and_set(hwnd)


def _switch_to(hwnd: int) -> None:
    """The alt+tab route. Undocumented, but shipped in user32 since forever."""
    _user32.SwitchToThisWindow(hwnd, True)


def _raise(hwnd: int) -> bool:
    """Put one window in front, escalating until Windows really obeys.

    ``SetForegroundWindow`` reports success while doing nothing whenever the
    foreground lock is in the way, so every attempt is checked against the window
    that actually ended up in front instead of trusting the return value.
    """
    if _user32.IsIconic(hwnd):
        _user32.ShowWindow(hwnd, SW_RESTORE)
    for attempt in (_attach_and_set, _nudge_and_set, _switch_to):
        try:
            attempt(hwnd)
        except Exception:  # noqa: BLE001 - try the next route
            log.debug("%s did not work", attempt.__name__, exc_info=True)
            continue
        time.sleep(0.05)  # the switch is not instant
        if _user32.GetForegroundWindow() == hwnd:
            log.debug("window raised by %s", attempt.__name__)
            return True
    return False


def raise_titled(title: str, skip_pid: int | None = None) -> bool:
    """Bring to the front a window with that exact title, ignoring one process.

    Used to hand the user back the configurator window that is already open when a
    second one is launched. It goes by title rather than by executable because in
    development the executable is python.exe, shared with anything else.
    """
    if not IS_WINDOWS:
        return False
    found: list[int] = []

    def visit(hwnd, _param):
        if _user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(300)
            _user32.GetWindowTextW(hwnd, buf, len(buf))
            if buf.value == title:
                pid = wintypes.DWORD()
                _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value != skip_pid:
                    found.append(hwnd)
        return True

    try:
        _user32.EnumWindows(_ENUM_PROC(visit), 0)
    except Exception:  # noqa: BLE001
        log.debug("could not walk the windows", exc_info=True)
        return False
    return bool(found) and _raise(found[0])


def raise_app(exe: str, wait_timeout: float = 12.0) -> None:
    """Bring a window of that executable to the front, without blocking.

    Waiting and asking are kept apart on purpose. A browser that is already
    running has its window right away, while a cold start takes several seconds,
    so the wait is generous. Asking, on the other hand, is done twice at most:
    Windows makes the taskbar button flash on every refusal, and a retry loop
    turns that into a very visible blinking.

    Runs in its own thread: the key press must not wait for a browser to boot.
    """
    if not (IS_WINDOWS and exe):
        return

    def worker() -> None:
        try:
            deadline = time.monotonic() + wait_timeout
            while not _windows_of(exe):        # only waits, does not touch focus
                if time.monotonic() > deadline:
                    log.debug("no window of %s showed up", exe)
                    return
                time.sleep(0.15)
            for _ in range(2):
                windows = _windows_of(exe)     # refreshed: a cold start may have
                if not windows:                # replaced its first window
                    return
                if _user32.GetForegroundWindow() in windows:
                    return                     # already in front, nothing to do
                if _raise(windows[0]):
                    return
                time.sleep(0.5)
            log.debug("windows refused to bring %s to the front", exe)
        except Exception:  # noqa: BLE001 - focus is a nicety, never a failure
            log.debug("could not raise %s", exe, exc_info=True)

    threading.Thread(target=worker, daemon=True).start()
