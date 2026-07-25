"""Native HID flasher (Windows), with no Zadig and no external drivers.

Opens the keyboard's programming interface (MI_00, usage page 0xFF00) through the
native Windows HID API (via hidapi) and writes the same message sequence that
ch57x-keyboard-tool would produce, but as HID reports.

Framing (confirmed by reading the device's HID caps):
- OutputReportByteLength = 65 and there are no feature reports.
- The leading 0x03 of every ch57x message IS the HID Report ID, not payload.
- So each write is 65 bytes: the 64 byte message plus one padding byte. Do NOT
  prepend a 0x00 report id (that shifts everything and Windows rejects it).
- The all zeros init message is skipped: report id 0x00 is not valid here.

See docs/PROTOCOL.md for the full description.
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
    """HID path of the programming interface (MI_00), or None if it is not there."""
    import hid

    for d in hid.enumerate(vid, pid):
        if d.get("usage_page") == PROGRAMMING_USAGE_PAGE:
            return d["path"]
    return None


def is_connected(vid: int = VID, pid: int = PID) -> bool:
    return find_programming_path(vid, pid) is not None


def set_led(color: str, mode: str = "backlight", layer: int = 0,
            vid: int = VID, pid: int = PID) -> None:
    """Change ONLY the lighting, without rewriting the key bindings (about 20 ms).

    Used for the press feedback: the whole keyboard takes the colour of the control
    you pressed and goes back to the layer colour right after. Writing the bindings
    too would take far too long for that.
    """
    import hid

    path = find_programming_path(vid, pid)
    if path is None:
        raise HidFlasherError("keyboard not connected")

    code = protocol.led_code(mode, color)
    messages = [
        bytes([0x03, 0xFE, 0xB0, layer + 1, 0x08, 0, 0, 0, 0, 0, 0x01, 0, code]),
        bytes([0x03, 0xFD, 0xFE, 0xFF]),
    ]
    dev = hid.device()
    dev.open_path(path)
    try:
        for msg in messages:
            dev.write(msg + bytes(protocol.MSG_LEN - len(msg)) + b"\x00")
    finally:
        dev.close()


def flash(profile: Profile, vid: int = VID, pid: int = PID, inter_delay: float = 0.002) -> int:
    """Write the profile into the keyboard over HID. Returns how many messages were sent."""
    import hid

    path = find_programming_path(vid, pid)
    if path is None:
        raise HidFlasherError(
            f"Cannot find the programming interface of {vid:04x}:{pid:04x} "
            "(usage page 0xFF00). Is the keyboard plugged in?"
        )

    messages = protocol.build_messages(profile) + protocol.build_led_messages(profile)
    dev = hid.device()
    try:
        dev.open_path(path)
    except OSError as exc:
        raise HidFlasherError(f"Could not open the programming interface: {exc}") from exc

    try:
        written = 0
        for msg in messages:
            # The first byte of a ch57x message (0x03) is the HID Report ID and the
            # rest is payload. Windows expects OutputReportByteLength (65) bytes, so
            # one padding byte is appended. The 'init' message starts with 0x00 (not
            # a valid HID report id) and is skipped: it does not apply to this path.
            if msg[0] == 0x00:
                continue
            report = msg + b"\x00"  # [0x03 report id] + payload + pad = 65 bytes
            n = dev.write(report)
            if n != len(report):
                raise HidFlasherError(
                    f"incomplete write: {n} of {len(report)} bytes (message {written})"
                )
            written += 1
            if inter_delay:
                time.sleep(inter_delay)
        log.info("flashed %d messages over HID", written)
        return written
    finally:
        dev.close()
