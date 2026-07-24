"""Arranque automático en Windows: la app de bandeja se inicia sola al entrar.

Crea un acceso directo en la carpeta de Inicio del usuario que ejecuta
``pythonw -m hotkeyconfig run`` (sin ventana de consola). Así, con el teclado
conectado, las configuraciones se aplican solas sin abrir nada a mano.
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
    """Crea el acceso directo de arranque. Devuelve su ruta."""
    try:
        import win32com.client  # de pywin32
    except ImportError as exc:
        raise RuntimeError(
            "El arranque automático necesita pywin32 (pip install pywin32)."
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
    sc.Description = "hotkeyconfig — listener de macropad (local y privado)"
    sc.Save()
    return lnk


def uninstall() -> bool:
    """Elimina el acceso directo de arranque. Devuelve True si existía."""
    lnk = shortcut_path()
    if lnk.exists():
        lnk.unlink()
        return True
    return False
