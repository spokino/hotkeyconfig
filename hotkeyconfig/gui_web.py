"""Configurador gráfico moderno (pywebview + WebView2).

Renderiza la interfaz web de ``webui/`` en una ventana nativa y expone un puente
con Python (``Api``) para leer/guardar el perfil, flashear y manejar el listener.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from . import hid_flasher
from .profile import Profile, load, save

HERE = Path(__file__).resolve().parent
INDEX = HERE / "webui" / "index.html"


def _pythonw() -> str:
    cand = Path(sys.executable).with_name("pythonw.exe")
    return str(cand if cand.exists() else sys.executable)


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
                [_pythonw(), "-m", "hotkeyconfig", "run", "--no-tray", "-p", str(self.profile_path)])
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
