"""Action executors used by the runtime.

Every action in ``profile.yaml`` is turned into something concrete here: launching
a script, opening an app or URL, typing text, sending a media key and so on.
``native`` actions (stored in the keyboard itself) and ``unassigned`` ones do not
normally reach this module; they are treated as no-ops for safety.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
import webbrowser
from typing import Any

log = logging.getLogger("hotkeyconfig.actions")

# Friendly names -> names used by the `keyboard` library.
_MEDIA_KEYS = {
    "volume_up": "volume up",
    "volume_down": "volume down",
    "mute": "volume mute",
    "play_pause": "play/pause media",
    "next": "next track",
    "previous": "previous track",
    "prev": "previous track",
    "stop": "stop media",
}


def execute(action) -> None:
    """Run an :class:`~hotkeyconfig.profile.Action`. Never raises: it logs instead."""
    try:
        handler = _HANDLERS.get(action.type)
        if handler is None:
            log.warning("action type with no executor: %s", action.type)
            return
        handler(action.params)
    except Exception:  # noqa: BLE001 - one action must not take the runtime down
        log.exception("failed running action %s", action.type)


def _run(p: dict[str, Any]) -> None:
    cmd = p.get("cmd")
    args = p.get("args")
    cwd = p.get("cwd")
    shell = bool(p.get("shell", False))
    if args:  # safe form: argument list, no shell
        subprocess.Popen(args, cwd=cwd)
    elif cmd:
        subprocess.Popen(cmd, cwd=cwd, shell=shell)
    else:
        log.warning("'run' action without 'cmd' or 'args'")


def _open(p: dict[str, Any]) -> None:
    target = p.get("target", "")
    if not target:
        log.warning("'open' action without 'target'")
        return
    if target.startswith(("http://", "https://")):
        webbrowser.open(target)
    else:
        os.startfile(os.path.expandvars(target))  # type: ignore[attr-defined]


def _text(p: dict[str, Any]) -> None:
    import keyboard  # lazy import: only needed at runtime
    text = p.get("text", "")
    keyboard.write(text, delay=p.get("delay", 0))


def _media(p: dict[str, Any]) -> None:
    import keyboard
    key = p.get("key") or p.get("do", "")
    name = _MEDIA_KEYS.get(key, key)
    keyboard.send(name)


def _hotkey(p: dict[str, Any]) -> None:
    import keyboard
    send = p.get("send", "")
    if send:
        keyboard.send(send)


def _window(p: dict[str, Any]) -> None:
    try:
        import win32con
        import win32gui
    except ImportError:
        log.warning("'window' actions need pywin32 (pip install pywin32)")
        return
    do = p.get("do", "")
    hwnd = win32gui.GetForegroundWindow()
    cmd = {
        "minimize": win32con.SW_MINIMIZE,
        "maximize": win32con.SW_MAXIMIZE,
        "restore": win32con.SW_RESTORE,
    }.get(do)
    if cmd is not None:
        win32gui.ShowWindow(hwnd, cmd)
    elif do == "close":
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    else:
        log.warning("unknown window operation: %s", do)


def _sequence(p: dict[str, Any]) -> None:
    from .profile import Action  # lazy import to avoid a cycle
    for step in p.get("steps", []):
        execute(Action.from_dict(step))
        delay = step.get("delay")
        if delay:
            time.sleep(delay)


def _noop(p: dict[str, Any]) -> None:
    return None


_HANDLERS = {
    "run": _run,
    "open": _open,
    "text": _text,
    "media": _media,
    "hotkey": _hotkey,
    "window": _window,
    "sequence": _sequence,
    "native": _noop,      # handled by the hardware itself
    "unassigned": _noop,
}
