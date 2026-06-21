"""Puente con ``ch57x-keyboard-tool``: traduce el perfil y lo graba en el teclado.

No reimplementamos el protocolo USB: generamos el YAML que entiende la
herramienta open source y se lo pasamos por stdin a sus subcomandos
``validate`` y ``upload``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import yaml

from . import combos
from .profile import Action, Profile

# Acciones "nativas" amistosas -> token multimedia de ch57x.
_NATIVE_ALIASES = {
    "volume_up": "volumeup",
    "volume_down": "volumedown",
    "play_pause": "play",
    "previous": "prev",
}

# Rutas donde buscar el binario si no está en el PATH.
_CANDIDATE_DIRS = [
    Path.home() / ".cargo" / "bin",
    Path(__file__).resolve().parent.parent / "vendor",
]


class FlasherError(RuntimeError):
    pass


def find_binary() -> str:
    """Localiza el ejecutable ch57x-keyboard-tool o lanza un error claro."""
    exe = "ch57x-keyboard-tool"
    found = shutil.which(exe) or shutil.which(exe + ".exe")
    if found:
        return found
    for d in _CANDIDATE_DIRS:
        for name in (exe, exe + ".exe"):
            cand = d / name
            if cand.exists():
                return str(cand)
    raise FlasherError(
        "No encuentro 'ch57x-keyboard-tool'. Instálalo con:\n"
        "    cargo install ch57x-keyboard-tool --locked\n"
        "o coloca el binario en ./vendor/."
    )


def _ch57x_key(action: Action, combo: str) -> str:
    """Token de ch57x para un control: la tecla nativa o el combo único."""
    if action.type == "native":
        key = action.params.get("key", "")
        return _NATIVE_ALIASES.get(key, key)
    return combos.to_ch57x(combo)


def build_config(profile: Profile) -> dict:
    """Construye el dict de configuración en el formato exacto de ch57x 1.7.0."""
    dev = profile.device
    cfg: dict = {
        "orientation": "normal",
        "rows": dev.rows,
        "columns": dev.columns,
        "knobs": dev.knobs,
        "layers": [],
    }
    for layer in profile.layers:
        # 12 botones planos -> filas x columnas (orden row-major).
        flat = [_ch57x_key(b.action, b.combo) for b in layer.buttons]
        rows = [
            flat[r * dev.columns : (r + 1) * dev.columns]
            for r in range(dev.rows)
        ]
        knobs = [
            {
                act: _ch57x_key(kb[act].action, kb[act].combo)
                for act in combos.KNOB_ACTIONS
            }
            for kb in layer.knobs
        ]
        cfg["layers"].append({"buttons": rows, "knobs": knobs})
    return cfg


def to_yaml(profile: Profile) -> str:
    return yaml.safe_dump(build_config(profile), sort_keys=False, allow_unicode=True)


def _run_tool(args: list[str], config_yaml: str) -> subprocess.CompletedProcess:
    binary = find_binary()
    env = {**os.environ, "PATH": os.environ.get("PATH", "")}
    return subprocess.run(
        [binary, *args],
        input=config_yaml,
        capture_output=True,
        text=True,
        env=env,
    )


def validate(profile: Profile) -> None:
    """Valida el mapeo con la propia herramienta antes de grabar."""
    result = _run_tool(["validate"], to_yaml(profile))
    if result.returncode != 0:
        raise FlasherError(f"validate falló:\n{result.stderr or result.stdout}")


def flash(profile: Profile) -> str:
    """Valida y graba el perfil en el teclado. Devuelve la salida de la herramienta."""
    profile.validate()
    validate(profile)
    result = _run_tool(["upload"], to_yaml(profile))
    if result.returncode != 0:
        raise FlasherError(f"upload falló:\n{result.stderr or result.stdout}")
    return result.stdout or "OK"
