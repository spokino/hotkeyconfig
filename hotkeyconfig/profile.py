"""Modelo y (de)serialización del perfil de usuario (``profile.yaml``).

El perfil es la **única fuente de verdad**: por cada capa describe, para cada
botón y cada acción de perilla, el combo único asignado y la acción a ejecutar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from . import combos

# Tipos de acción reconocidos. "native" se graba directamente en el teclado
# (no pasa por el runtime); el resto se disparan al detectar el combo único.
ACTION_TYPES = {
    "unassigned",  # sin asignar (no hace nada)
    "run",         # ejecutar script/comando
    "open",        # abrir app, carpeta o URL
    "text",        # escribir/pegar texto
    "media",       # tecla multimedia (vía runtime)
    "native",      # tecla nativa grabada en el HW (volumen, etc.)
    "hotkey",      # enviar un atajo a la app activa
    "window",      # operación de ventana (minimizar, etc.)
    "sequence",    # varias acciones en orden
}


@dataclass
class Action:
    type: str = "unassigned"
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.type not in ACTION_TYPES:
            raise ValueError(
                f"tipo de accion desconocido: {self.type!r} "
                f"(validos: {sorted(ACTION_TYPES)})"
            )

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Action":
        if not data:
            return cls()
        data = dict(data)
        type_ = data.pop("type", "unassigned")
        return cls(type=type_, params=data)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, **self.params}


@dataclass
class Binding:
    combo: str
    action: Action

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Binding":
        return cls(combo=data["combo"], action=Action.from_dict(data.get("action")))

    def to_dict(self) -> dict[str, Any]:
        return {"combo": self.combo, "action": self.action.to_dict()}


@dataclass
class Layer:
    name: str
    buttons: list[Binding]
    knobs: list[dict[str, Binding]]  # por perilla: {ccw, press, cw} -> Binding

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Layer":
        buttons = [Binding.from_dict(b) for b in data["buttons"]]
        knobs = [
            {act: Binding.from_dict(k[act]) for act in combos.KNOB_ACTIONS}
            for k in data["knobs"]
        ]
        return cls(name=data.get("name", ""), buttons=buttons, knobs=knobs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "buttons": [b.to_dict() for b in self.buttons],
            "knobs": [
                {act: kb[act].to_dict() for act in combos.KNOB_ACTIONS}
                for kb in self.knobs
            ],
        }


@dataclass
class Device:
    name: str = "AliExpress ch57x macropad"
    vid: str = "1189"
    pid: str = "8842"
    rows: int = combos.ROWS
    columns: int = combos.COLUMNS
    knobs: int = combos.KNOBS

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Device":
        return cls(**{k: data[k] for k in data if k in cls.__annotations__})

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "vid": self.vid, "pid": self.pid,
            "rows": self.rows, "columns": self.columns, "knobs": self.knobs,
        }


@dataclass
class Profile:
    device: Device
    layers: list[Layer]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Profile":
        return cls(
            device=Device.from_dict(data.get("device", {})),
            layers=[Layer.from_dict(layer) for layer in data["layers"]],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "device": self.device.to_dict(),
            "layers": [layer.to_dict() for layer in self.layers],
        }

    def iter_bindings(self):
        """Recorre (label, Binding) de todos los controles, todas las capas."""
        for li, layer in enumerate(self.layers, start=1):
            for bi, binding in enumerate(layer.buttons, start=1):
                yield (f"C{li}/tecla{bi}", binding)
            for ki, knob in enumerate(layer.knobs, start=1):
                for act in combos.KNOB_ACTIONS:
                    yield (f"C{li}/perilla{ki}/{act}", knob[act])

    def validate(self) -> None:
        """Comprueba unicidad de combos y consistencia del layout."""
        seen: dict[str, str] = {}
        for label, binding in self.iter_bindings():
            if binding.combo in seen:
                raise ValueError(
                    f"combo duplicado {binding.combo!r}: {label} y {seen[binding.combo]}"
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
