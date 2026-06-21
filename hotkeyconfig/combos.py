"""Generador de combinaciones únicas para el macropad ch57x.

Concepto: estos macropads emiten pulsaciones HID estándar, no un ID por tecla.
Para hacer cada control "único" le asignamos una combinación que ningún teclado
físico produce: las teclas fantasma ``F13``..``F24`` (existen en HID pero no en
hardware real) acompañadas de familias de modificadores distintas por capa.

- Botones: familias de modificadores SIN la tecla Win.
- Perillas: familias de modificadores CON la tecla Win.

Como las dos familias nunca se solapan, los 54 combos resultantes
(12 botones x 3 capas + 2 perillas x 3 acciones x 3 capas) son únicos por
construcción. Los combos se guardan en una forma canónica ("ctrl+alt+f13") y se
traducen al formato de cada destino con :func:`to_ch57x` y :func:`to_keyboard`.
"""

from __future__ import annotations

# --- Layout físico de esta familia de macropad (ch57x 3x4 + 2 perillas) ---
ROWS = 3
COLUMNS = 4
KNOBS = 2
LAYERS = 3
KNOB_ACTIONS = ("ccw", "press", "cw")  # giro antihorario, click, giro horario

# F13..F24: válidas en HID, ausentes en teclados reales -> "huecos" libres.
_FKEYS = [f"f{n}" for n in range(13, 25)]  # 12 teclas

# Una familia de modificadores por capa para los BOTONES (sin Win).
_BUTTON_MODS = {
    0: ("ctrl", "alt"),
    1: ("ctrl", "shift"),
    2: ("alt", "shift"),
}
# Una familia por capa para las PERILLAS (siempre con Win -> nunca choca con un botón).
_KNOB_MODS = {
    0: ("ctrl", "win"),
    1: ("alt", "win"),
    2: ("shift", "win"),
}

# Traducción de modificadores canónicos al nombre que usa la librería `keyboard`.
_KEYBOARD_MOD_ALIASES = {"win": "windows"}


def button_combo(layer: int, index: int) -> str:
    """Combo único para el botón ``index`` (0..11) de la ``layer`` (0..2)."""
    if not 0 <= layer < LAYERS:
        raise ValueError(f"capa fuera de rango: {layer}")
    if not 0 <= index < ROWS * COLUMNS:
        raise ValueError(f"indice de boton fuera de rango: {index}")
    mods = _BUTTON_MODS[layer]
    return "+".join([*mods, _FKEYS[index]])


def knob_combo(layer: int, knob: int, action: str) -> str:
    """Combo único para una acción de perilla (``ccw``/``press``/``cw``)."""
    if action not in KNOB_ACTIONS:
        raise ValueError(f"accion de perilla invalida: {action}")
    mods = _KNOB_MODS[layer]
    slot = knob * len(KNOB_ACTIONS) + KNOB_ACTIONS.index(action)  # 0..5
    return "+".join([*mods, _FKEYS[slot]])


def all_combos() -> list[str]:
    """Lista de los 54 combos en orden determinista (para validar unicidad)."""
    combos: list[str] = []
    for layer in range(LAYERS):
        for index in range(ROWS * COLUMNS):
            combos.append(button_combo(layer, index))
        for knob in range(KNOBS):
            for action in KNOB_ACTIONS:
                combos.append(knob_combo(layer, knob, action))
    return combos


def assert_unique() -> None:
    """Comprueba en arranque que el esquema no produce colisiones."""
    combos = all_combos()
    if len(combos) != len(set(combos)):
        dupes = sorted({c for c in combos if combos.count(c) > 1})
        raise AssertionError(f"combos duplicados en el esquema: {dupes}")


def to_ch57x(combo: str) -> str:
    """Forma canónica -> formato de ch57x-keyboard-tool (modificadores con '-')."""
    return "-".join(combo.split("+"))


def to_keyboard(combo: str) -> str:
    """Forma canónica -> formato de la librería `keyboard` (alias de Win)."""
    tokens = [_KEYBOARD_MOD_ALIASES.get(t, t) for t in combo.split("+")]
    return "+".join(tokens)
