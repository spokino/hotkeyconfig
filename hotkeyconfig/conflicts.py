"""Key combinations Windows, or another program, has already taken.

Two different problems share one answer here.

The first is the one people actually notice: recording ``Ctrl+Shift+Win+B`` for a
key and finding out that Windows uses it to restart the graphics driver, so the
screen blinks black every time. Windows has dozens of these and nobody has them
memorised.

The second is quieter. The combos this program writes into the keyboard look
random (``ctrl+alt+f13`` and friends) precisely so that nothing else uses them,
but "nothing else" is not guaranteed: on the machine this was written on, seven
of the fifty four were already taken by other software. A key with a taken combo
simply does nothing, and there is no way to tell by looking.

``RegisterHotKey`` answers both: if Windows refuses a combination with error 1409
somebody else holds it, whether that somebody is the system or another program.
Nothing is left registered, so asking is free of side effects. The list of names
below only serves to say *which* system shortcut it is, in words.

The listener does not use this module: it grabs keys with a low level hook, which
is a different mechanism and does not fight with these registrations.
"""

from __future__ import annotations

import ctypes
import logging
import sys

log = logging.getLogger("hotkeyconfig.conflicts")

IS_WINDOWS = sys.platform == "win32"

_MOD_BITS = {"alt": 0x0001, "ctrl": 0x0002, "shift": 0x0004, "win": 0x0008}
_MOD_NOREPEAT = 0x4000
_ERROR_HOTKEY_ALREADY_REGISTERED = 1409

# What the interface may hand us for the same modifier.
_MOD_ALIASES = {
    "control": "ctrl", "ctl": "ctrl",
    "windows": "win", "meta": "win", "super": "win", "cmd": "win",
    "option": "alt", "alt gr": "alt", "altgr": "alt",
}
_MOD_ORDER = ("ctrl", "alt", "shift", "win")

_VK = {f"f{n}": 0x6F + n for n in range(1, 25)}          # F1 = 0x70 ... F24 = 0x87
_VK.update({chr(c).lower(): c for c in range(ord("A"), ord("Z") + 1)})
_VK.update({str(d): ord(str(d)) for d in range(10)})
_VK.update({
    "space": 0x20, "esc": 0x1B, "escape": 0x1B, "enter": 0x0D, "return": 0x0D,
    "tab": 0x09, "backspace": 0x08, "delete": 0x2E, "del": 0x2E, "insert": 0x2D,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "home": 0x24, "end": 0x23, "page up": 0x21, "page down": 0x22,
    "caps lock": 0x14, "print screen": 0x2C, "prtsc": 0x2C, "pause": 0x13,
    "-": 0xBD, "=": 0xBB, ",": 0xBC, ".": 0xBE, "/": 0xBF, ";": 0xBA,
    "'": 0xDE, "[": 0xDB, "]": 0xDD, "\\": 0xDC, "`": 0xC0,
})

# System shortcuts worth naming. The key is the reason it is worth naming: the
# interface turns it into a sentence in the user's language. Windows holds many
# more, and RegisterHotKey catches those too; these are only the ones common
# enough to deserve an explanation instead of a bare "somebody has it".
_SYSTEM: dict[str, str] = {
    "ctrl+shift+win+b": "reset_gpu",
    "win+b": "notification_area",
    "win+d": "show_desktop",
    "win+e": "file_explorer",
    "win+i": "settings",
    "win+l": "lock",
    "win+r": "run",
    "win+s": "search",
    "win+q": "search",
    "win+a": "quick_settings",
    "win+n": "notifications",
    "win+v": "clipboard",
    "win+g": "game_bar",
    "win+h": "dictation",
    "win+x": "power_menu",
    "win+m": "minimize_all",
    "win+p": "project",
    "win+tab": "task_view",
    "win+print screen": "screenshot",
    "win+shift+s": "snip",
    "win+.": "emoji",
    "win+,": "peek_desktop",
    "win+left": "snap_window",
    "win+right": "snap_window",
    "win+up": "snap_window",
    "win+down": "snap_window",
    "ctrl+shift+esc": "task_manager",
    "ctrl+alt+delete": "security_screen",
    "alt+tab": "switch_window",
    "alt+f4": "close_window",
    "alt+esc": "cycle_windows",
    "ctrl+esc": "start_menu",
}


def normalise(combo: str) -> str:
    """Canonical form: modifiers in a fixed order, one spelling each.

    The same combination arrives written three ways (the interface says
    ``windows``, profiles say ``win``, people type them in any order), and
    comparing them as text would miss half the conflicts.
    """
    if not combo:
        return ""
    parts = [p.strip().lower() for p in str(combo).split("+") if p.strip()]
    if not parts:
        return ""
    parts = [_MOD_ALIASES.get(p, p) for p in parts]
    mods = {p for p in parts if p in _MOD_BITS}
    keys = [p for p in parts if p not in _MOD_BITS]
    ordered = [m for m in _MOD_ORDER if m in mods]
    return "+".join([*ordered, *keys])


def _split(combo: str) -> tuple[int, int] | None:
    """(modifier mask, virtual key) or None when we cannot express it."""
    parts = normalise(combo).split("+")
    if not parts or not parts[-1]:
        return None
    key = _VK.get(parts[-1])
    if key is None:
        return None
    mask = 0
    for part in parts[:-1]:
        bit = _MOD_BITS.get(part)
        if bit is None:
            return None
        mask |= bit
    return mask, key


def system_shortcut(combo: str) -> str:
    """Name of the Windows shortcut this combination is, or an empty string."""
    return _SYSTEM.get(normalise(combo), "")


def is_taken(combo: str) -> bool:
    """Does anything else already hold this combination?

    Asked by registering it and letting it go straight away. A combination we
    cannot even express (an unknown key name) is reported as free: refusing to
    save something on a doubt would be worse than the conflict itself.
    """
    if not IS_WINDOWS:
        return False
    if normalise(combo) in _SYSTEM:
        return True
    pieces = _split(combo)
    if pieces is None:
        return False
    mask, key = pieces
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    hotkey_id = 0xC0DE
    if user32.RegisterHotKey(None, hotkey_id, mask | _MOD_NOREPEAT, key):
        user32.UnregisterHotKey(None, hotkey_id)
        return False
    return ctypes.get_last_error() == _ERROR_HOTKEY_ALREADY_REGISTERED


def check(combo: str, ignore: set[str] | None = None) -> dict:
    """Report on one combination: ``{"combo", "taken", "system"}``."""
    canonical = normalise(combo)
    if ignore and canonical in {normalise(c) for c in ignore}:
        return {"combo": canonical, "taken": False, "system": ""}
    return {"combo": canonical, "taken": is_taken(combo),
            "system": system_shortcut(combo)}


def taken_among(combos: list[str], ignore: set[str] | None = None) -> set[str]:
    """The canonical combinations, out of those given, that somebody else holds."""
    skip = {normalise(c) for c in (ignore or set())}
    busy = set()
    for combo in combos:
        canonical = normalise(combo)
        if canonical in skip or canonical in busy:
            continue
        if is_taken(combo):
            busy.add(canonical)
    return busy
