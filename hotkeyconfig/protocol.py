"""Constructor de los mensajes USB del protocolo ch57x (familia k884x).

Porta byte a byte la lógica de ``kriomant/ch57x-keyboard-tool`` (módulo
``keyboard/k884x.rs``) para no inventar el protocolo. Produce la lista de
mensajes de 64 bytes idéntica a la que envía esa herramienta; el transporte
(libusb vs HID) lo decide quien consuma esta lista.

Referencia de la fuente original (1.7.0):
- cada mensaje se rellena a 64 bytes y empieza por 0x03.
- bind de tecla: [0x03, 0xfe, key_id, layer+1, kind, 0,0,0,0,0, count, mod, code]
- media:         [0x03, 0xfe, key_id, layer+1, 0x02, 0,0,0,0,0, 0, low, high, 0,0,0,0]
- cierre por tecla: 0xaa/0xaa · 0xfd/0xfe/0xff · 0xaa/0xaa
- key_id: botones 1..12; perilla k (0-based) acción a (ccw=0,press=1,cw=2) -> 16+3k+a
"""

from __future__ import annotations

from .profile import Profile

MSG_LEN = 64

# Bits de modificador (orden del enum Modifier de ch57x).
_MOD_BITS = {"ctrl": 0x01, "shift": 0x02, "alt": 0x04, "win": 0x08}

# Códigos HID de F13..F24 (F13 = 0x68, secuencial).
_FCODE = {f"f{n}": 0x68 + (n - 13) for n in range(13, 25)}

# Códigos "consumer" multimedia (enum MediaCode de ch57x), como u16.
_MEDIA = {
    "next": 0xB5, "previous": 0xB6, "prev": 0xB6, "stop": 0xB7, "play": 0xCD,
    "play_pause": 0xCD, "mute": 0xE2, "volume_up": 0xE9, "volumeup": 0xE9,
    "volume_down": 0xEA, "volumedown": 0xEA, "favorites": 0x182,
    "calculator": 0x192, "screenlock": 0x19E,
}

_KNOB_ACTION_INDEX = {"ccw": 0, "press": 1, "cw": 2}


def _pad(msg: list[int]) -> bytes:
    if len(msg) > MSG_LEN:
        raise ValueError(f"mensaje demasiado largo: {len(msg)}")
    return bytes(msg) + bytes(MSG_LEN - len(msg))


def _button_key_id(index: int) -> int:
    return index + 1  # botón 0 -> id 1 … botón 11 -> id 12


def _knob_key_id(knob: int, action: str) -> int:
    return 16 + 3 * knob + _KNOB_ACTION_INDEX[action]


def _parse_combo(combo: str) -> tuple[int, int]:
    """'ctrl+alt+f13' -> (byte de modificadores, código HID de la tecla)."""
    mod = 0
    code = 0
    for token in combo.split("+"):
        if token in _MOD_BITS:
            mod |= _MOD_BITS[token]
        elif token in _FCODE:
            code = _FCODE[token]
        else:
            raise ValueError(f"token de combo no soportado: {token!r} en {combo!r}")
    return mod, code


def _bind_messages(layer: int, key_id: int, binding) -> list[bytes]:
    action = binding.action
    if action.type == "native":
        key = action.params.get("key", "")
        if key not in _MEDIA:
            raise ValueError(f"tecla nativa no soportada: {key!r}")
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
    """Devuelve la secuencia completa de mensajes de 64 bytes (incluido el init)."""
    profile.validate()
    messages: list[bytes] = [_pad([])]  # init: 64 ceros
    for layer_idx, layer in enumerate(profile.layers):
        for btn_idx, binding in enumerate(layer.buttons):
            messages += _bind_messages(layer_idx, _button_key_id(btn_idx), binding)
        for knob_idx, knob in enumerate(layer.knobs):
            for action in ("ccw", "press", "cw"):
                messages += _bind_messages(
                    layer_idx, _knob_key_id(knob_idx, action), knob[action]
                )
    return messages
