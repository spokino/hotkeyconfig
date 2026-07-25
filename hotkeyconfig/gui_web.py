"""Configurador gráfico moderno (pywebview + WebView2).

Renderiza la interfaz web de ``webui/`` en una ventana nativa y expone un puente
con Python (``Api``) para leer/guardar el perfil, flashear y manejar el listener.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from . import hid_flasher
from ._appcmd import app_command
from .profile import Profile, load, save

HERE = Path(__file__).resolve().parent
INDEX = HERE / "webui" / "index.html"


class Api:
    def __init__(self, profile_path: str | Path):
        self.profile_path = Path(profile_path)
        self.listener: subprocess.Popen | None = None

    # --- perfil ---------------------------------------------------------
    def get_profile(self) -> dict:
        if self.profile_path.exists():
            return load(self.profile_path).to_dict()
        from .cli import build_default_profile
        prof = build_default_profile()
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        save(prof, self.profile_path)
        return prof.to_dict()

    def save_profile(self, data: dict) -> dict:
        try:
            prof = Profile.from_dict(data)
            prof.validate()
            save(prof, self.profile_path)
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def flash(self, data: dict) -> dict:
        try:
            prof = Profile.from_dict(data)
            prof.validate()
            save(prof, self.profile_path)
            if not hid_flasher.is_connected():
                return {"ok": False, "error": "No veo el teclado conectado."}
            n = hid_flasher.flash(prof)
            return {"ok": True, "n": n}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def test_action(self, action_dict: dict) -> dict:
        """Ejecuta una acción una vez, para probarla desde la GUI."""
        try:
            from . import actions
            from .profile import Action
            actions.execute(Action.from_dict(action_dict))
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def resize_layout(self, current: dict, rows: int, columns: int, knobs: int, orientation: str) -> dict:
        """Cambia la estructura conservando acciones, luz y atajos (regenera combos)."""
        from .cli import build_default_profile
        from .profile import Device, Profile
        old = Profile.from_dict(current)
        dev = Device(rows=int(rows), columns=int(columns), knobs=int(knobs), orientation=orientation)
        new = build_default_profile(dev)
        for li, layer in enumerate(new.layers):
            if li >= len(old.layers):
                break
            old_layer = old.layers[li]
            for bi, binding in enumerate(layer.buttons):
                if bi < len(old_layer.buttons):
                    binding.action = old_layer.buttons[bi].action
            for ki, knob in enumerate(layer.knobs):
                if ki < len(old_layer.knobs):
                    for act in ("ccw", "press", "cw"):
                        knob[act].action = old_layer.knobs[ki][act].action
            layer.led = old_layer.led
        new.hotkeys = old.hotkeys
        new.remaps = old.remaps
        save(new, self.profile_path)
        return new.to_dict()

    # --- estado / listener ---------------------------------------------
    def status(self) -> dict:
        running = self.listener is not None and self.listener.poll() is None
        try:
            connected = hid_flasher.is_connected()
        except Exception:  # noqa: BLE001
            connected = False
        return {"connected": connected, "listener": running}

    def start_listener(self) -> dict:
        if not (self.listener and self.listener.poll() is None):
            self.listener = subprocess.Popen(
                app_command("run", "--no-tray", "-p", str(self.profile_path)))
        return {"listener": True}

    def stop_listener(self) -> dict:
        if self.listener:
            self.listener.terminate()
            self.listener = None
        return {"listener": False}


def run(profile_path: str | Path) -> int:
    import webview

    api = Api(profile_path)
    webview.create_window(
        "hotkeyconfig", url=str(INDEX), js_api=api,
        width=900, height=710, min_size=(780, 600),
        background_color="#16161a",
    )
    webview.start()
    return 0
