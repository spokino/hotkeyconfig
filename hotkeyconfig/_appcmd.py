"""How to re-invoke the app itself, whether it runs as a script or as a frozen .exe.

In development the app relaunches with `pythonw -m hotkeyconfig <args>`. Once
packaged with PyInstaller, `-m hotkeyconfig` does not exist: the executable has to
be called with the subcommand arguments. This helper returns the right command for
each case.
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_command(*args: str) -> list[str]:
    """Command that launches an app subcommand (e.g. app_command('run', '--no-tray'))."""
    if is_frozen():
        return [sys.executable, *args]
    pyw = Path(sys.executable).with_name("pythonw.exe")
    exe = str(pyw if pyw.exists() else sys.executable)
    return [exe, "-m", "hotkeyconfig", *args]


def app_target() -> tuple[str, str]:
    """(executable, argument prefix) for Windows shortcuts."""
    if is_frozen():
        return sys.executable, ""
    pyw = Path(sys.executable).with_name("pythonw.exe")
    exe = str(pyw if pyw.exists() else sys.executable)
    return exe, "-m hotkeyconfig"
