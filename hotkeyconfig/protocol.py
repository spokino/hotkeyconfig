"""Builder for the ch57x (k884x family) USB messages.

Ports the logic of ``kriomant/ch57x-keyboard-tool`` (module ``keyboard/k884x.rs``)
byte for byte, so the protocol is not guessed. It produces the same list of 64
byte messages that tool sends; the transport (libusb vs HID) is up to whoever
consumes the list. See docs/PROTOCOL.md for the human readable description.

Reference from the original source (1.7.0):
- every message is padded to 64 bytes and starts with 0x03.
- key bind: [0x03, 0xfe, key_id, layer+1, kind, 0,0,0,0,0, count, mod, code]
- media:    [0x03, 0xfe, key_id, layer+1, 0x02, 0,0,0,0,0, 0, low, high, 0,0,0,0]
- per key tail: 0xaa/0xaa, 0xfd/0xfe/0xff, 0xaa/0xaa
- key_id: buttons 1..12; knob k (zero based) action a (ccw=0, press=1, cw=2) -> 16+3k+a
"""

from __future__ import annotations

from .profile import Profile

MSG_LEN = 64

# Modifier bits (order of the ch57x Modifier enum).
_MOD_BITS = {"ctrl": 0x01, "shift": 0x02, "alt": 0x04, "win": 0x08}

# HID codes for F13..F24 (F13 = 0x68, sequential).
_FCODE = {f"f{n}": 0x68 + (n - 13) for n in range(13, 25)}

# Consumer media codes (ch57x MediaCode enum), as u16.
_MEDIA = {
    "next": 0xB5, "previous": 0xB6, "prev": 0xB6, "stop": 0xB7, "play": 0xCD,
    "play_pause": 0xCD, "mute": 0xE2, "volume_up": 0xE9, "volumeup": 0xE9,
    "volume_down": 0xEA, "volumedown": 0xEA, "favorites": 0x182,
    "calculator": 0x192, "screenlock": 0x19E,
}

_KNOB_ACTION_INDEX = {"ccw": 0, "press": 1, "cw": 2}

# --- Lighting (LED). Ported from k884x.rs set_led / LedMode.code(). ---
LED_MODES = ("off", "backlight", "shock", "shock2", "press")
LED_COLORS = ("white", "red", "orange", "yellow", "green", "cyan", "blue", "purple")
_LED_MODE_CODE = {"off": 0, "backlight": 1, "shock": 2, "shock2": 3, "press": 4}
_LED_COLOR_CODE = {c: i for i, c in enumerate(LED_COLORS)}  # white=0 … purple=7


def led_code(mode: str, color: str) -> int:
    """Lighting code: (color << 4) | mode. 'backlight white' is a special case (5)."""
    if mode == "off":
        return 0
    if mode == "backlight" and color == "white":
        return 5
    m = _LED_MODE_CODE.get(mode, 1)
    c = _LED_COLOR_CODE.get(color, _LED_COLOR_CODE["blue"])
    return (c << 4) | m


def build_led_messages(profile) -> list[bytes]:
    """Messages that write the lighting of every layer that has an LED configured."""
    msgs: list[bytes] = []
    for layer_idx, layer in enumerate(profile.layers):
        led = layer.led
        if not led:
            continue
        code = led_code(led.get("mode", "off"), led.get("color", "blue"))
        msgs.append(_pad([0x03, 0xFE, 0xB0, layer_idx + 1, 0x08, 0x00, 0x05, 0x01, 0x00, code, 0x00, 0x34]))
        msgs.append(_pad([0x03, 0xFD, 0xFE, 0xFF, 0x00, 0x3D]))
    return msgs


def _pad(msg: list[int]) -> bytes:
    if len(msg) > MSG_LEN:
        raise ValueError(f"message too long: {len(msg)}")
    return bytes(msg) + bytes(MSG_LEN - len(msg))


def _button_key_id(index: int) -> int:
    return index + 1  # button 0 -> id 1 … button 11 -> id 12


def _knob_key_id(knob: int, action: str, buttons: int) -> int:
    # On 12 button boards the 4th knob reuses ids 13 to 15 (a ch57x quirk).
    if knob == 3 and buttons <= 12:
        return 13 + _KNOB_ACTION_INDEX[action]
    return 16 + 3 * knob + _KNOB_ACTION_INDEX[action]


def _parse_combo(combo: str) -> tuple[int, int]:
    """'ctrl+alt+f13' -> (modifier byte, HID key code)."""
    mod = 0
    code = 0
    for token in combo.split("+"):
        if token in _MOD_BITS:
            mod |= _MOD_BITS[token]
        elif token in _FCODE:
            code = _FCODE[token]
        else:
            raise ValueError(f"unsupported combo token: {token!r} in {combo!r}")
    return mod, code


def _bind_messages(layer: int, key_id: int, binding) -> list[bytes]:
    action = binding.action
    if action.type == "native":
        key = action.params.get("key", "")
        if key not in _MEDIA:
            raise ValueError(f"unsupported native key: {key!r}")
        low, high = (_MEDIA[key] & 0xFFFF).to_bytes(2, "little")
        head = [0x03, 0xFE, key_id, layer + 1, 0x02, 0, 0, 0, 0, 0, 0, low, high, 0, 0, 0, 0]
    else:
        mod, code = _parse_combo(binding.combo)
        head = [0x03, 0xFE, key_id, layer + 1, 0x01, 0, 0, 0, 0, 0, 1, mod, code]
    return [
        _pad(head),
        _pad([0x03, 0xAA, 0xAA]),
        _pad([0x03, 0xFD, 0xFE, 0xFF]),
        _pad([0x03, 0xAA, 0xAA]),
    ]


def build_messages(profile: Profile) -> list[bytes]:
    """Return the full sequence of 64 byte messages (the init one included)."""
    profile.validate()
    buttons = profile.device.rows * profile.device.columns
    messages: list[bytes] = [_pad([])]  # init: 64 zeros
    for layer_idx, layer in enumerate(profile.layers):
        for btn_idx, binding in enumerate(layer.buttons):
            messages += _bind_messages(layer_idx, _button_key_id(btn_idx), binding)
        for knob_idx, knob in enumerate(layer.knobs):
            for action in ("ccw", "press", "cw"):
                messages += _bind_messages(
                    layer_idx, _knob_key_id(knob_idx, action, buttons), knob[action]
                )
    return messages
