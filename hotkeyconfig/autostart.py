"""Start with Windows: the tray app launches on its own when you log in.

Creates a shortcut in the user's Startup folder that runs
``pythonw -m hotkeyconfig run`` (no console window). That way, with the keyboard
plugged in, your bindings work without opening anything by hand.
"""

from __future__ import annotations

import os
from pathlib import Path

from ._appcmd import app_target

SHORTCUT_NAME = "hotkeyconfig.lnk"


def _startup_dir() -> Path:
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def shortcut_path() -> Path:
    return _startup_dir() / SHORTCUT_NAME


def is_installed() -> bool:
    return shortcut_path().exists()


def install(profile: str | None = None) -> Path:
    """Create the startup shortcut. Returns its path."""
    try:
        import win32com.client  # from pywin32
    except ImportError as exc:
        raise RuntimeError(
            "Autostart needs pywin32 (pip install pywin32)."
        ) from exc

    exe, prefix = app_target()
    args = (prefix + " run").strip()
    if profile:
        args += f' --profile "{profile}"'

    target = _startup_dir()
    target.mkdir(parents=True, exist_ok=True)
    lnk = shortcut_path()

    shell = win32com.client.Dispatch("WScript.Shell")
    sc = shell.CreateShortcut(str(lnk))
    sc.TargetPath = exe
    sc.Arguments = args
    sc.WorkingDirectory = str(Path(__file__).resolve().parent.parent)
    sc.Description = "hotkeyconfig: macropad listener (local and private)"
    sc.Save()
    return lnk


def uninstall() -> bool:
    """Remove the startup shortcut. Returns True if it existed."""
    lnk = shortcut_path()
    if lnk.exists():
        lnk.unlink()
        return True
    return False
