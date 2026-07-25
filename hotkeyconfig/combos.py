"""Generador de combinaciones únicas para macropads ch57x (layout configurable).

Concepto: estos macropads emiten pulsaciones HID estándar, no un ID por tecla.
Para hacer cada control "único" le asignamos una combinación que ningún teclado
físico produce: las teclas fantasma ``F13``..``F24`` (existen en HID pero no en
hardware real) con familias de modificadores.

- Botones: familias de modificadores SIN la tecla Win.
- Perillas: familias de modificadores CON la tecla Win.

Como las dos familias nunca se solapan y a cada control se le asigna un
``(familia, tecla-F)`` distinto por su índice global, todos los combos son únicos
por construcción, para cualquier layout dentro de los límites de ch57x
(hasta 15 botones y 3 perillas, o 12 botones y 4 perillas). El esquema es
retrocompatible: un layout 3x4 + 2 perillas produce los mismos combos de siempre.
"""

from __future__ import annotations

# --- Layout por defecto (familia ch57x 3x4 + 2 perillas) ---
ROWS = 3
COLUMNS = 4
KNOBS = 2
LAYERS = 3
KNOB_ACTIONS = ("ccw", "press", "cw")  # giro antihorario, click, giro horario
ORIENTATIONS = ("normal", "upsidedown", "clockwise", "counterclockwise")

# F13..F24: válidas en HID, ausentes en teclados reales -> "huecos" libres.
_FKEYS = [f"f{n}" for n in range(13, 25)]  # 12 teclas

# Familias de modificadores. Botones sin Win; perillas con Win -> nunca chocan.
# El orden fija la asignación determinista (retrocompatible con el esquema previo).
_BUTTON_FAMILIES = [("ctrl", "alt"), ("ctrl", "shift"), ("alt", "shift"), ("ctrl", "alt", "shift")]
_KNOB_FAMILIES = [("ctrl", "win"), ("alt", "win"), ("shift", "win"), ("ctrl", "alt", "win")]

_KEYBOARD_MOD_ALIASES = {"win": "windows"}

# Capacidad: cada familia cubre 12 teclas-F.
_CAPACITY = len(_FKEYS)


def _alloc(families: list[tuple], slot: int) -> str:
    """Asigna determinísticamente un combo (familia, tecla-F) al índice global ``slot``."""
    fam_idx, fk_idx = divmod(slot, _CAPACITY)
    if fam_idx >= len(families):
        raise ValueError("layout demasiado grande para el esquema de combos únicos")
    return "+".join([*families[fam_idx], _FKEYS[fk_idx]])


def button_combo(layer: int, index: int, buttons_per_layer: int = ROWS * COLUMNS) -> str:
    """Combo único para el botón ``index`` de la ``layer`` (0-based)."""
    return _alloc(_BUTTON_FAMILIES, layer * buttons_per_layer + index)


def knob_combo(layer: int, knob: int, action: str, knobs: int = KNOBS) -> str:
    """Combo único para una acción de perilla (``ccw``/``press``/``cw``)."""
    if action not in KNOB_ACTIONS:
        raise ValueError(f"accion de perilla invalida: {action}")
    slot = layer * knobs * len(KNOB_ACTIONS) + knob * len(KNOB_ACTIONS) + KNOB_ACTIONS.index(action)
    return _alloc(_KNOB_FAMILIES, slot)


def all_combos(rows: int = ROWS, columns: int = COLUMNS, knobs: int = KNOBS,
               layers: int = LAYERS) -> list[str]:
    """Todos los combos del layout, en orden determinista (para validar unicidad)."""
    per_layer = rows * columns
    combos: list[str] = []
    for layer in range(layers):
        for index in range(per_layer):
            combos.append(button_combo(layer, index, per_layer))
        for knob in range(knobs):
            for action in KNOB_ACTIONS:
                combos.append(knob_combo(layer, knob, action, knobs))
    return combos


def assert_unique(rows: int = ROWS, columns: int = COLUMNS, knobs: int = KNOBS,
                  layers: int = LAYERS) -> None:
    """Comprueba que el layout no produce colisiones de combos."""
    combos = all_combos(rows, columns, knobs, layers)
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
