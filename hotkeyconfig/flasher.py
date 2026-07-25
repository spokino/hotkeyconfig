"""Bridge to ``ch57x-keyboard-tool``: translates the profile and writes it to the keyboard.

This is the OPTIONAL backend. The default path is native HID (see hid_flasher.py),
which needs no external binary. Here the USB protocol is not reimplemented: we
generate the YAML that the open source tool understands and pipe it to its
``validate`` and ``upload`` subcommands over stdin.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import yaml

from . import combos
from .profile import Action, Profile

# Friendly "native" action names -> ch57x media tokens.
_NATIVE_ALIASES = {
    "volume_up": "volumeup",
    "volume_down": "volumedown",
    "play_pause": "play",
    "previous": "prev",
}

# Where to look for the binary when it is not on PATH.
_CANDIDATE_DIRS = [
    Path.home() / ".cargo" / "bin",
    Path(__file__).resolve().parent.parent / "vendor",
]


class FlasherError(RuntimeError):
    pass


def find_binary() -> str:
    """Locate the ch57x-keyboard-tool executable, or raise a clear error."""
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
        "Cannot find 'ch57x-keyboard-tool'. Install it with:\n"
        "    cargo install ch57x-keyboard-tool --locked\n"
        "or drop the binary into ./vendor/."
    )


def _ch57x_key(action: Action, combo: str) -> str:
    """ch57x token for one control: either the native key or the unique combo."""
    if action.type == "native":
        key = action.params.get("key", "")
        return _NATIVE_ALIASES.get(key, key)
    return combos.to_ch57x(combo)


def build_config(profile: Profile) -> dict:
    """Build the configuration dict in the exact format of ch57x 1.7.0."""
    dev = profile.device
    cfg: dict = {
        "orientation": "normal",
        "rows": dev.rows,
        "columns": dev.columns,
        "knobs": dev.knobs,
        "layers": [],
    }
    for layer in profile.layers:
        # Flat button list -> rows x columns (row major order).
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
    """Validate the mapping with the tool itself before writing anything."""
    result = _run_tool(["validate"], to_yaml(profile))
    if result.returncode != 0:
        raise FlasherError(f"validate failed:\n{result.stderr or result.stdout}")


def flash(profile: Profile) -> str:
    """Validate and write the profile to the keyboard. Returns the tool's output."""
    profile.validate()
    validate(profile)
    result = _run_tool(["upload"], to_yaml(profile))
    if result.returncode != 0:
        raise FlasherError(f"upload failed:\n{result.stderr or result.stdout}")
    return result.stdout or "OK"
