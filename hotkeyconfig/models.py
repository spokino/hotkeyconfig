"""Catalogue of known macropad models.

These boards are sold under dozens of names with no model number anywhere, so
they are listed here by what the user can actually see and count: how many keys,
how many knobs, how they are arranged. Picking from this list beats typing in a
grid size, because a 7x9 macropad does not exist and nothing good comes from
letting someone configure one.

Two things are kept apart on purpose:

- The **protocol family**, decided by the USB identifiers. It is what the device
  understands on the wire, and the program detects it, never the user.
- The **shape**, which the user picks. The same identifiers ship in several
  shapes, so the hardware cannot be asked: a `1189:8842` may have 12 keys and
  2 knobs, or 9 keys and 2 knobs.

Sources for the identifiers and shapes: the model table in `kriomant/
ch57x-keyboard-tool` and the reports in its issue tracker.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- Protocol families -----------------------------------------------------
# k884x is the one this program implements and the one verified against real
# hardware. The other two are listed so the program can recognise the device and
# say so plainly, instead of pretending it does not exist.
K884X = "k884x"
K8890 = "k8890"
K8850_4X4 = "k8850_4x4"

FAMILIES = {
    # family: [(vendor, product), ...]
    K884X: [(0x1189, 0x8840), (0x1189, 0x8842), (0x1189, 0x8850), (0x514C, 0x8851)],
    K8890: [(0x1189, 0x8890)],
    K8850_4X4: [(0x514C, 0x8850)],
}

SUPPORTED_FAMILIES = (K884X,)   # the rest are recognised, not yet supported


@dataclass(frozen=True)
class Model:
    """One shape of macropad, as the user would describe it."""
    id: str
    rows: int
    columns: int
    knobs: int
    family: str = K884X
    layers: int = 3
    note: str = ""            # translation key for a caveat, if any

    @property
    def keys(self) -> int:
        return self.rows * self.columns

    def to_device_fields(self) -> dict:
        return {"rows": self.rows, "columns": self.columns, "knobs": self.knobs}


# Ordered small to large: the list reads like a shelf of products.
CATALOGUE: list[Model] = [
    Model("3k1n", rows=1, columns=3, knobs=1, note="note_single_modifier"),
    Model("4k0n", rows=1, columns=4, knobs=0),
    Model("6k1n", rows=2, columns=3, knobs=1),
    Model("9k2n", rows=3, columns=3, knobs=2),
    Model("12k2n", rows=3, columns=4, knobs=2),   # the most common one
    Model("12k3n", rows=3, columns=4, knobs=3),
    Model("15k3n", rows=3, columns=5, knobs=3),
    Model("16k3n", rows=4, columns=4, knobs=3, family=K8850_4X4),
]

CUSTOM = "custom"   # the escape hatch: unknown variant, sizes set by hand
DEFAULT_MODEL = "12k2n"

_BY_ID = {m.id: m for m in CATALOGUE}


def get(model_id: str | None) -> Model | None:
    """The model with that id, or None for a custom or unknown one."""
    return _BY_ID.get(model_id or "")


def family_of(vid: int, pid: int) -> str | None:
    """Protocol family of a vendor:product pair, or None if unknown."""
    for family, pairs in FAMILIES.items():
        if (vid, pid) in pairs:
            return family
    return None


def known_pairs(families: tuple[str, ...] = SUPPORTED_FAMILIES) -> list[tuple[int, int]]:
    """Every vendor:product of those families, to scan for a plugged in device."""
    return [pair for family in families for pair in FAMILIES.get(family, [])]


def matching(model_id: str | None, rows: int, columns: int, knobs: int) -> str:
    """Work out which model a profile describes, for profiles saved before this list.

    Older profiles only carry the grid size, so the shape is matched back to a
    model. Anything that matches nothing is custom, which is exactly what it is.
    """
    if model_id == CUSTOM:
        return CUSTOM        # picked on purpose, not second guessed
    chosen = _BY_ID.get(model_id or "")
    # The stored id is only kept if it still matches the shape. Otherwise the two
    # would drift apart and the interface would claim 12 keys over a grid of 9.
    if chosen and (chosen.rows, chosen.columns, chosen.knobs) == (rows, columns, knobs):
        return chosen.id
    for model in CATALOGUE:
        if (model.rows, model.columns, model.knobs) == (rows, columns, knobs):
            return model.id
    return CUSTOM
