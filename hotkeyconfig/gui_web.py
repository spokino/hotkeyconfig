"""Modern visual configurator (pywebview + WebView2).

Renders the web interface from ``webui/`` inside a native window and exposes a
bridge to Python (``Api``) to read and save the profile, flash the keyboard and
drive the listener.
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

    # --- profile ---------------------------------------------------------
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
            if hid_flasher.resolve(prof) is None:
                other = hid_flasher.detect_unsupported()
                if other:
                    return {"ok": False, "error":
                            f"Your keyboard ({other['vid']:04x}:{other['pid']:04x}) is "
                            f"recognised, but its {other['family']} protocol is not "
                            "supported yet."}
                return {"ok": False, "error": "I cannot see the keyboard connected."}
            n = hid_flasher.flash(prof)
            return {"ok": True, "n": n}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def models(self) -> list[dict]:
        """The catalogue of keyboard shapes, for the model picker."""
        from . import models as models_mod
        return [{"id": m.id, "keys": m.keys, "rows": m.rows, "columns": m.columns,
                 "knobs": m.knobs, "family": m.family, "note": m.note,
                 "supported": m.family in models_mod.SUPPORTED_FAMILIES}
                for m in models_mod.CATALOGUE]

    def browsers(self) -> list[dict]:
        """Installed browsers, to pick one in an 'open' action."""
        from . import browsers as browsers_mod
        try:
            return browsers_mod.list_browsers()
        except Exception:  # noqa: BLE001 - the list is optional, the default always works
            return []

    def test_action(self, action_dict: dict) -> dict:
        """Run an action once, so it can be tested from the GUI."""
        try:
            from . import actions
            from .profile import Action
            actions.execute(Action.from_dict(action_dict))
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def resize_layout(self, current: dict, rows: int, columns: int, knobs: int, orientation: str) -> dict:
        """Change the layout keeping actions, lighting and shortcuts (combos are regenerated)."""
        from .cli import build_default_profile
        from .profile import Device, Profile
        old = Profile.from_dict(current)
        # Name and USB ids belong to the keyboard, not to its shape: rebuilding the
        # device from scratch used to reset them to the defaults, which now matters
        # because several different vendor:product pairs are supported.
        dev = Device(name=old.device.name, vid=old.device.vid, pid=old.device.pid,
                     model=old.device.model, rows=int(rows), columns=int(columns),
                     knobs=int(knobs), orientation=orientation,
                     knob_side=old.device.knob_side)
        new = build_default_profile(dev)
        for li, layer in enumerate(new.layers):
            if li >= len(old.layers):
                break
            old_layer = old.layers[li]
            for bi, binding in enumerate(layer.buttons):
                if bi < len(old_layer.buttons):
                    binding.action = old_layer.buttons[bi].action
                    binding.color = old_layer.buttons[bi].color
            for ki, knob in enumerate(layer.knobs):
                if ki < len(old_layer.knobs):
                    for act in ("ccw", "press", "cw"):
                        knob[act].action = old_layer.knobs[ki][act].action
                        knob[act].color = old_layer.knobs[ki][act].color
            layer.led = old_layer.led
        new.hotkeys = old.hotkeys
        new.remaps = old.remaps
        save(new, self.profile_path)
        return new.to_dict()

    # --- status / listener -----------------------------------------------
    def check_update(self) -> dict:
        from . import updater
        return updater.check_for_update()

    def apply_update(self) -> dict:
        from . import updater
        return updater.apply_update()

    def open_url(self, url: str) -> dict:
        import webbrowser
        webbrowser.open(url)
        return {"ok": True}

    def status(self) -> dict:
        running = self.listener is not None and self.listener.poll() is None
        found = unsupported = None
        try:
            found = hid_flasher.detect()
            if found is None:
                unsupported = hid_flasher.detect_unsupported()
        except Exception:  # noqa: BLE001
            pass
        return {
            "connected": found is not None,
            "listener": running,
            # A recognised keyboard that cannot be programmed yet deserves a clearer
            # message than "not connected".
            "usb": f"{found['vid']:04x}:{found['pid']:04x}" if found else
                   (f"{unsupported['vid']:04x}:{unsupported['pid']:04x}" if unsupported else ""),
            "unsupported": unsupported["family"] if unsupported else "",
        }

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


def _free_port() -> int:
    """A port nobody else is using, asked to the system.

    pywebview serves the interface from a local HTTP server on a fixed port, and
    when that port is already taken it cheerfully loads from whoever is answering
    there. With two versions of the program open, the newer window ends up showing
    the interface of the older one: new logic, old controls, and hours lost
    chasing a bug that was never in the code. One server per window avoids it.
    """
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run(profile_path: str | Path) -> int:
    import os

    import webview

    # Turning off the HTTP cache: since the interface files sit next to the program,
    # WebView2 was serving the previous version of the interface after an update
    # while the Python side was already the new one. There is nothing to gain by
    # caching a handful of local files.
    os.environ.setdefault("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "--disable-http-cache")

    api = Api(profile_path)
    webview.create_window(
        # Nombre para la gente. El paquete, el comando y el repositorio siguen
        # siendo hotkeyconfig en minusculas: eso es un identificador, no un rotulo.
        "HotKeyConfig", url=str(INDEX), js_api=api,
        width=900, height=710, min_size=(780, 600),
        background_color="#16161a",
    )
    # private_mode=False so localStorage (language and so on) survives between sessions;
    # with the default private mode it was wiped on close. storage_path points at a
    # writable user folder (not the program directory, which can be read only).
    storage = os.path.join(os.environ.get("LOCALAPPDATA") or str(Path.home()), "hotkeyconfig", "webview")
    webview.start(private_mode=False, storage_path=storage, http_port=_free_port())
    return 0
