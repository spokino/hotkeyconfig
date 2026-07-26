"""Installed browsers (Windows only).

Windows lists the browsers in the registry under ``Clients\\StartMenuInternet``,
the same place the Settings app reads, and records the chosen one in the https
``UserChoice`` association. Both are read here so an ``open`` action can either
follow the system default or force a specific browser.

Nothing here raises: an unreadable registry just means an empty list, and the
action falls back to the system default.
"""

from __future__ import annotations

import logging
import os
import sys

log = logging.getLogger("hotkeyconfig.browsers")

IS_WINDOWS = sys.platform == "win32"

_START_MENU = r"Software\Clients\StartMenuInternet"
_URL_CHOICE = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice"

if IS_WINDOWS:
    import winreg


def _exe_from_command(command: str) -> str:
    """Pull the executable out of a registry command line."""
    command = command.strip()
    if command.startswith('"'):
        return command[1:].split('"', 1)[0]
    return command.split(" ", 1)[0]


def _read(root, path: str, value: str = "") -> str:
    try:
        with winreg.OpenKey(root, path) as key:
            return str(winreg.QueryValueEx(key, value)[0])
    except OSError:
        return ""


def list_browsers() -> list[dict[str, str]]:
    """Installed browsers as ``{"name", "path"}``, without duplicates."""
    if not IS_WINDOWS:
        return []
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            key = winreg.OpenKey(root, _START_MENU)
        except OSError:
            continue
        with key:
            for index in range(winreg.QueryInfoKey(key)[0]):
                try:
                    entry = winreg.EnumKey(key, index)
                except OSError:
                    break
                path = _exe_from_command(
                    _read(root, rf"{_START_MENU}\{entry}\shell\open\command"))
                if not path or not os.path.isfile(path) or path.lower() in seen:
                    continue
                seen.add(path.lower())
                found.append({
                    "name": _read(root, rf"{_START_MENU}\{entry}") or entry,
                    "path": path,
                })
    return sorted(found, key=lambda b: b["name"].lower())


def default_browser() -> str:
    """Path of the browser Windows uses for https links, or an empty string."""
    if not IS_WINDOWS:
        return ""
    prog_id = _read(winreg.HKEY_CURRENT_USER, _URL_CHOICE, "ProgId")
    if not prog_id:
        return ""
    path = _exe_from_command(
        _read(winreg.HKEY_CLASSES_ROOT, rf"{prog_id}\shell\open\command"))
    return path if os.path.isfile(path) else ""


def resolve(value: str | None) -> str:
    """Turn what the profile stores into an executable path.

    Accepts a full path or the browser name shown in the interface. An empty
    value means the system default, which is handled by the caller.
    """
    if not value:
        return ""
    value = os.path.expandvars(value.strip())
    if os.path.isfile(value):
        return value
    wanted = value.lower()
    for browser in list_browsers():
        if wanted in (browser["name"].lower(), os.path.basename(browser["path"]).lower()):
            return browser["path"]
    log.warning("browser not found: %r, using the system default", value)
    return ""
