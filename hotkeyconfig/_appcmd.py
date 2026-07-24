"""Cómo re-invocar la propia app, funcione como script o como .exe congelado.

En desarrollo la app se relanza con `pythonw -m hotkeyconfig <args>`. Empaquetada
con PyInstaller, `-m hotkeyconfig` no existe: hay que llamar al propio ejecutable
con los argumentos del subcomando. Este helper devuelve la orden correcta en cada caso.
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_command(*args: str) -> list[str]:
    """Orden para lanzar un subcomando de la app (p. ej. app_command('run', '--no-tray'))."""
    if is_frozen():
        return [sys.executable, *args]
    pyw = Path(sys.executable).with_name("pythonw.exe")
    exe = str(pyw if pyw.exists() else sys.executable)
    return [exe, "-m", "hotkeyconfig", *args]


def app_target() -> tuple[str, str]:
    """(ejecutable, prefijo de argumentos) para accesos directos de Windows."""
    if is_frozen():
        return sys.executable, ""
    pyw = Path(sys.executable).with_name("pythonw.exe")
    exe = str(pyw if pyw.exists() else sys.executable)
    return exe, "-m hotkeyconfig"
