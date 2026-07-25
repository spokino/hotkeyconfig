"""Unique combo generator for ch57x macropads (configurable layout).

The idea: these macropads send standard HID keystrokes, not a per key id. To make
every control "unique" we assign it a combo no physical keyboard can produce: the
phantom keys ``F13``..``F24`` (they exist in HID but not on real hardware) paired
with modifier families.

- Buttons: modifier families WITHOUT the Win key.
- Knobs: modifier families WITH the Win key.

Since the two families never overlap and each control gets a distinct
``(family, F key)`` from its global index, every combo is unique by construction,
for any layout within the ch57x limits (up to 15 buttons and 3 knobs, or 12
buttons and 4 knobs). The scheme is backwards compatible: a 3x4 layout with 2
knobs produces exactly the same combos as before.
"""

from __future__ import annotations

# --- Default layout (the common ch57x board: 3x4 plus 2 knobs) ---
ROWS = 3
COLUMNS = 4
KNOBS = 2
LAYERS = 3
KNOB_ACTIONS = ("ccw", "press", "cw")  # turn counter clockwise, click, turn clockwise
ORIENTATIONS = ("normal", "upsidedown", "clockwise", "counterclockwise")

# F13..F24: valid in HID, absent from real keyboards, so they are free slots.
_FKEYS = [f"f{n}" for n in range(13, 25)]  # 12 keys

# Modifier families. Buttons without Win, knobs with Win, so they never collide.
# The order fixes the deterministic assignment (backwards compatible with the
# original scheme).
_BUTTON_FAMILIES = [("ctrl", "alt"), ("ctrl", "shift"), ("alt", "shift"), ("ctrl", "alt", "shift")]
_KNOB_FAMILIES = [("ctrl", "win"), ("alt", "win"), ("shift", "win"), ("ctrl", "alt", "win")]

_KEYBOARD_MOD_ALIASES = {"win": "windows"}

# Capacity: every family covers 12 F keys.
_CAPACITY = len(_FKEYS)


def _alloc(families: list[tuple], slot: int) -> str:
    """Deterministically assign a (family, F key) combo to the global index ``slot``."""
    fam_idx, fk_idx = divmod(slot, _CAPACITY)
    if fam_idx >= len(families):
        raise ValueError("layout too large for the unique combo scheme")
    return "+".join([*families[fam_idx], _FKEYS[fk_idx]])


def button_combo(layer: int, index: int, buttons_per_layer: int = ROWS * COLUMNS) -> str:
    """Unique combo for button ``index`` of ``layer`` (both zero based)."""
    return _alloc(_BUTTON_FAMILIES, layer * buttons_per_layer + index)


def knob_combo(layer: int, knob: int, action: str, knobs: int = KNOBS) -> str:
    """Unique combo for one knob action (``ccw`` / ``press`` / ``cw``)."""
    if action not in KNOB_ACTIONS:
        raise ValueError(f"invalid knob action: {action}")
    slot = layer * knobs * len(KNOB_ACTIONS) + knob * len(KNOB_ACTIONS) + KNOB_ACTIONS.index(action)
    return _alloc(_KNOB_FAMILIES, slot)


def all_combos(rows: int = ROWS, columns: int = COLUMNS, knobs: int = KNOBS,
               layers: int = LAYERS) -> list[str]:
    """Every combo of the layout, in deterministic order (used to check uniqueness)."""
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
    """Check that the layout does not produce combo collisions."""
    combos = all_combos(rows, columns, knobs, layers)
    if len(combos) != len(set(combos)):
        dupes = sorted({c for c in combos if combos.count(c) > 1})
        raise AssertionError(f"duplicated combos in the scheme: {dupes}")


def to_ch57x(combo: str) -> str:
    """Canonical form to the ch57x-keyboard-tool format (modifiers joined with '-')."""
    return "-".join(combo.split("+"))


def to_keyboard(combo: str) -> str:
    """Canonical form to the `keyboard` library format (Win alias)."""
    tokens = [_KEYBOARD_MOD_ALIASES.get(t, t) for t in combo.split("+")]
    return "+".join(tokens)
