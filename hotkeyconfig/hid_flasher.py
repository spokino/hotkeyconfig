"""Flasher nativo por HID (Windows) — sin Zadig ni drivers externos.

Abre la interfaz de programación del teclado (MI_00, usage page 0xFF00) con la
API HID nativa de Windows (vía hidapi) y le escribe la misma secuencia de
mensajes que generaría ch57x-keyboard-tool, pero como reportes HID.

Framing (confirmado leyendo las HID caps del dispositivo):
- OutputReportByteLength = 65 y no hay feature reports.
- El 0x03 inicial de ch57x es el primer byte de DATOS, no un Report ID HID.
- Por tanto cada escritura son 65 bytes: [0x00 (report id)] + mensaje de 64.
"""

from __future__ import annotations

import logging
import time

from . import protocol
from .profile import Profile

log = logging.getLogger("hotkeyconfig.hid_flasher")

VID = 0x1189
PID = 0x8842
PROGRAMMING_USAGE_PAGE = 0xFF00


class HidFlasherError(RuntimeError):
    pass


def find_programming_path(vid: int = VID, pid: int = PID) -> bytes | None:
    """Ruta HID de la interfaz de programación (MI_00) o None si no aparece."""
    import hid

    for d in hid.enumerate(vid, pid):
        if d.get("usage_page") == PROGRAMMING_USAGE_PAGE:
            return d["path"]
    return None


def is_connected(vid: int = VID, pid: int = PID) -> bool:
    return find_programming_path(vid, pid) is not None


def flash(profile: Profile, vid: int = VID, pid: int = PID, inter_delay: float = 0.002) -> int:
    """Graba el perfil en el teclado por HID. Devuelve el nº de mensajes escritos."""
    import hid

    path = find_programming_path(vid, pid)
    if path is None:
        raise HidFlasherError(
            f"No encuentro la interfaz de programación de {vid:04x}:{pid:04x} "
            "(usage page 0xFF00). ¿Está el teclado enchufado?"
        )

    messages = protocol.build_messages(profile) + protocol.build_led_messages(profile)
    dev = hid.device()
    try:
        dev.open_path(path)
    except OSError as exc:
        raise HidFlasherError(f"No pude abrir la interfaz de programación: {exc}") from exc

    try:
        written = 0
        for msg in messages:
            # El primer byte del mensaje ch57x (0x03) es el Report ID HID; el
            # resto son datos. Windows espera OutputReportByteLength (65) bytes,
            # así que añadimos 1 byte de relleno. El mensaje 'init' empieza por
            # 0x00 (report id inválido en HID) y se omite: no aplica a esta vía.
            if msg[0] == 0x00:
                continue
            report = msg + b"\x00"  # [0x03 (report id)] + datos + pad = 65 bytes
            n = dev.write(report)
            if n != len(report):
                raise HidFlasherError(
                    f"escritura incompleta: {n} de {len(report)} bytes (mensaje {written})"
                )
            written += 1
            if inter_delay:
                time.sleep(inter_delay)
        log.info("flasheados %d mensajes por HID", written)
        return written
    finally:
        dev.close()
