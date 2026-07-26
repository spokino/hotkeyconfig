"""Model and (de)serialization of the user profile (``profile.yaml``).

The profile is the **single source of truth**: for every layer it describes, for
every button and every knob action, the unique combo assigned to it and the
action to run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from . import combos, models

# Recognised action types. "native" is written straight into the keyboard (it does
# not go through the runtime); the rest fire when the unique combo is detected.
ACTION_TYPES = {
    "unassigned",  # nothing bound (does nothing)
    "run",         # run a script or command
    "open",        # open an app, folder or URL
    "text",        # type or paste text
    "media",       # media key (through the runtime)
    "native",      # native key stored in the hardware (volume and so on)
    "hotkey",      # send a shortcut to the active app
    "window",      # window operation (minimize and so on)
    "sequence",    # several actions in order
}


@dataclass
class Action:
    type: str = "unassigned"
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.type not in ACTION_TYPES:
            raise ValueError(
                f"unknown action type: {self.type!r} "
                f"(valid ones: {sorted(ACTION_TYPES)})"
            )

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Action":
        if not data:
            return cls()
        data = dict(data)
        type_ = data.pop("type", "unassigned")
        # Up to 0.4.0 the web UI saved the fields inside a nested "params", while
        # everything else reads them at the top level, so those actions silently did
        # nothing. Both shapes are accepted here; to_dict always writes the flat one.
        nested = data.pop("params", None)
        if isinstance(nested, dict):
            data = {**data, **nested}
        return cls(type=type_, params=data)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, **self.params}


@dataclass
class Binding:
    combo: str
    action: Action
    # Color de aviso al pulsar este control. El ch57x no admite un color por tecla
    # en reposo, asi que el listener tine el teclado ENTERO un instante y lo devuelve
    # al color de la capa. Requiere que la capa tenga iluminacion configurada.
    color: str | None = None
    # Hand this key over to Windows through a shortcut with a hotkey, so it works
    # with nothing of ours running. Only for "open" actions. See standalone.py.
    standalone: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Binding":
        return cls(combo=data["combo"], action=Action.from_dict(data.get("action")),
                   color=data.get("color"), standalone=bool(data.get("standalone", False)))

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"combo": self.combo, "action": self.action.to_dict()}
        if self.color:
            out["color"] = self.color
        if self.standalone:
            out["standalone"] = True
        return out


@dataclass
class Layer:
    name: str
    buttons: list[Binding]
    knobs: list[dict[str, Binding]]  # per knob: {ccw, press, cw} -> Binding
    led: dict[str, Any] | None = None  # {mode, color} of the lighting (None = leave as is)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Layer":
        buttons = [Binding.from_dict(b) for b in data["buttons"]]
        knobs = [
            {act: Binding.from_dict(k[act]) for act in combos.KNOB_ACTIONS}
            for k in data["knobs"]
        ]
        return cls(name=data.get("name", ""), buttons=buttons, knobs=knobs,
                   led=data.get("led"))

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "name": self.name,
            "buttons": [b.to_dict() for b in self.buttons],
            "knobs": [
                {act: kb[act].to_dict() for act in combos.KNOB_ACTIONS}
                for kb in self.knobs
            ],
        }
        if self.led:
            out["led"] = self.led
        return out


@dataclass
class Device:
    name: str = "AliExpress ch57x macropad"
    vid: str = "1189"
    pid: str = "8842"
    rows: int = combos.ROWS
    columns: int = combos.COLUMNS
    knobs: int = combos.KNOBS
    orientation: str = "normal"  # normal | upsidedown | clockwise | counterclockwise (as mounted)
    # Where the knobs sit on the actual board. Only affects how it is drawn, but
    # a drawing that does not match what is on the desk is a drawing that lies.
    knob_side: str = "top"       # top | right | bottom | left
    # Which model of the catalogue this is. The grid above stays as the source of
    # truth so older profiles keep working; this only records what was picked.
    model: str = models.DEFAULT_MODEL

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Device":
        device = cls(**{k: data[k] for k in data if k in cls.__annotations__})
        # A profile written before the catalogue existed has no model, so it is
        # worked out from its shape.
        device.model = models.matching(data.get("model"), device.rows,
                                       device.columns, device.knobs)
        return device

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "vid": self.vid, "pid": self.pid,
            "model": self.model,
            "rows": self.rows, "columns": self.columns, "knobs": self.knobs,
            "orientation": self.orientation, "knob_side": self.knob_side,
        }

    def usb_ids(self) -> tuple[int, int]:
        """vendor and product as numbers. They are stored as hex text (``"1189"``)."""
        return int(str(self.vid), 16), int(str(self.pid), 16)


@dataclass
class Profile:
    device: Device
    layers: list[Layer]
    hotkeys: list[Binding] = field(default_factory=list)  # normal keyboard shortcuts
    remaps: list[dict[str, str]] = field(default_factory=list)  # [{from, to}] key remaps

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Profile":
        return cls(
            device=Device.from_dict(data.get("device", {})),
            layers=[Layer.from_dict(layer) for layer in data["layers"]],
            hotkeys=[Binding.from_dict(h) for h in data.get("hotkeys", [])],
            remaps=[dict(r) for r in data.get("remaps", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "device": self.device.to_dict(),
            "layers": [layer.to_dict() for layer in self.layers],
        }
        if self.hotkeys:
            out["hotkeys"] = [h.to_dict() for h in self.hotkeys]
        if self.remaps:
            out["remaps"] = [dict(r) for r in self.remaps]
        return out

    def iter_bindings(self):
        """Walk (label, Binding) over the macropad controls, across every layer."""
        for li, layer in enumerate(self.layers, start=1):
            for bi, binding in enumerate(layer.buttons, start=1):
                yield (f"L{li}/key{bi}", binding)
            for ki, knob in enumerate(layer.knobs, start=1):
                for act in combos.KNOB_ACTIONS:
                    yield (f"L{li}/knob{ki}/{act}", knob[act])

    def validate(self) -> None:
        """Check that the macropad combos are unique and the layout is consistent."""
        seen: dict[str, str] = {}
        for label, binding in self.iter_bindings():
            if binding.combo in seen:
                raise ValueError(
                    f"duplicated combo {binding.combo!r}: {label} and {seen[binding.combo]}"
                )
            seen[binding.combo] = label


def load(path: str | Path) -> Profile:
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    profile = Profile.from_dict(data)
    profile.validate()
    return profile


def save(profile: Profile, path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(
            profile.to_dict(), fh, sort_keys=False, allow_unicode=True, width=100
        )
