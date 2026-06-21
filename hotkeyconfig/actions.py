"""Ejecutores de acciones del runtime.

Cada acción del ``profile.yaml`` se traduce aquí en algo concreto: lanzar un
script, abrir una app/URL, escribir texto, enviar una tecla multimedia, etc.
Las acciones ``native`` (grabadas en el propio teclado) y ``unassigned`` no
pasan por aquí en condiciones normales; se tratan como no-op por seguridad.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
import webbrowser
from typing import Any

log = logging.getLogger("hotkeyconfig.actions")

# Nombres amistosos -> nombres de la librería `keyboard`.
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
    """Ejecuta una :class:`~hotkeyconfig.profile.Action`. Nunca lanza: registra."""
    try:
        handler = _HANDLERS.get(action.type)
        if handler is None:
            log.warning("tipo de accion sin ejecutor: %s", action.type)
            return
        handler(action.params)
    except Exception:  # noqa: BLE001 - una acción no debe tumbar el runtime
        log.exception("fallo ejecutando accion %s", action.type)


def _run(p: dict[str, Any]) -> None:
    cmd = p.get("cmd")
    args = p.get("args")
    cwd = p.get("cwd")
    shell = bool(p.get("shell", False))
    if args:  # forma segura: lista de argumentos, sin shell
        subprocess.Popen(args, cwd=cwd)
    elif cmd:
        subprocess.Popen(cmd, cwd=cwd, shell=shell)
    else:
        log.warning("accion 'run' sin 'cmd' ni 'args'")


def _open(p: dict[str, Any]) -> None:
    target = p.get("target", "")
    if not target:
        log.warning("accion 'open' sin 'target'")
        return
    if target.startswith(("http://", "https://")):
        webbrowser.open(target)
    else:
        os.startfile(os.path.expandvars(target))  # type: ignore[attr-defined]


def _text(p: dict[str, Any]) -> None:
    import keyboard  # import perezoso: solo se necesita en runtime
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
        log.warning("acciones 'window' requieren pywin32 (pip install pywin32)")
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
        log.warning("operacion de ventana desconocida: %s", do)


def _sequence(p: dict[str, Any]) -> None:
    from .profile import Action  # import perezoso para evitar ciclo
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
    "native": _noop,      # lo gestiona el hardware
    "unassigned": _noop,
}
