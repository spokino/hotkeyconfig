"""Modern visual configurator (pywebview + WebView2).

Renders the web interface from ``webui/`` inside a native window and exposes a
bridge to Python (``Api``) to read and save the profile, flash the keyboard and
drive the listener.
"""

from __future__ import annotations

import subprocess
import threading
import time
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
        # Copy of the profile while it has edits that are not on disk yet, so that
        # closing the window can offer to save them. See set_pending.
        self.pending: dict | None = None
        # Con guion bajo a proposito, y esto NO es cosmetica: pywebview construye el
        # puente recorriendo dir() de este objeto y, en cada atributo que sea un
        # objeto, entra dentro a buscar mas metodos. Guardar la ventana con nombre
        # publico le hacia recorrer la ventana entera al cargar: el arranque se
        # volvia lento y el puente acababa saliendo mal, con la interfaz en blanco.
        # Los nombres que empiezan por guion bajo se los salta.
        self._window = None         # se rellena en run()
        self.close_asked = False    # ya se pregunto que hacer con los cambios

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
            self.pending = None
            from . import standalone
            return {"ok": True, "standalone": standalone.sync(prof)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def save_device(self, device: dict) -> dict:
        """Write only the "this is my keyboard" settings, right when they change.

        The model, where the knobs sit and the orientation describe the hardware on
        the desk; they are not an edit in progress. Losing them on close because the
        Save button had not been pressed made no sense, the more so as changing the
        shape did save itself (through resize_layout) while these did not.

        Only the device section is touched: no binding is rewritten and no Windows
        shortcut is recreated, which is what makes saving on every change safe here.
        """
        try:
            prof = load(self.profile_path) if self.profile_path.exists() else None
            if prof is None:
                return {"ok": True}
            for name in ("model", "knob_side", "orientation"):
                if name in device:
                    setattr(prof.device, name, device[name])
            save(prof, self.profile_path)
            if self.pending:
                self.pending.setdefault("device", {}).update(prof.device.to_dict())
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def set_pending(self, data: dict | None) -> dict:
        """Mirror on this side whether there are unsaved edits, and which ones.

        Closing the window runs on the UI thread: asking the interface for its state
        right there would block it, so the interface pushes its state as it changes
        and closing only has to read a variable.
        """
        self.pending = data or None
        self.close_asked = False
        return {"ok": True}

    def keep_open(self) -> dict:
        """The interface asked and the answer was to go back to the app."""
        self.close_asked = False
        return {"ok": True}

    def close_window(self, save_first: bool) -> dict:
        """Close for real, once the interface has asked what to do with the changes."""
        if save_first and self.pending:
            result = self.save_profile(self.pending)
            if not result.get("ok"):
                return result      # se queda abierta y la interfaz canta el error
        self.pending = None
        if self._window is not None:
            # Fuera de esta llamada. Cerrar la ventana desde dentro de una llamada del
            # navegador la deja a medio contestar y Windows la marca como "no responde":
            # una ventana zombi que ya no se puede ni cerrar. Medido, dos veces.
            threading.Thread(target=self._destroy_soon, daemon=True).start()
        return {"ok": True}

    def _destroy_soon(self) -> None:
        time.sleep(0.2)     # que la respuesta llegue al navegador antes de matarlo
        try:
            self._window.destroy()
        except Exception:   # noqa: BLE001 - si ya no esta, mejor
            pass

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
                    # Also the "works with the app closed" mark: dropping it here left
                    # the key looking configured while its shortcut went stale.
                    binding.standalone = old_layer.buttons[bi].standalone
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

    def _listener_running(self) -> bool:
        """Is there a listener out there, ours or not.

        Asking only about our own subprocess used to lie whenever the listener had
        been started by Windows at login, and the button offered to start a second
        one, which would run every action twice.
        """
        from . import singleton
        if self.listener is not None and self.listener.poll() is None:
            return True
        return singleton.taken(singleton.LISTENER)

    def status(self) -> dict:
        running = self._listener_running()
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

    # --- que las teclas funcionen siempre ---------------------------------
    def autostart_status(self) -> dict:
        """Whether the listener starts with Windows. Without it the macropad is mute.

        This is the one thing that decides if the program keeps its promise: the
        combos live in the keyboard, but somebody has to be listening for them, and
        until now that somebody only existed while this window was open.
        """
        from . import autostart
        try:
            return {"enabled": autostart.is_installed()}
        except Exception:  # noqa: BLE001
            return {"enabled": False}

    def set_autostart(self, enabled: bool) -> dict:
        from . import autostart
        try:
            if enabled:
                autostart.install(str(self.profile_path))
                # Y que valga ya, no en el proximo inicio de sesion.
                self.start_listener()
            else:
                autostart.uninstall()
            return {"ok": True, "enabled": bool(enabled),
                    "listener": self._listener_running()}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def start_listener(self) -> dict:
        if not self._listener_running():
            self.listener = subprocess.Popen(
                app_command("run", "--no-tray", "-p", str(self.profile_path)))
        return {"listener": True}

    def stop_listener(self) -> dict:
        if self.listener:
            self.listener.terminate()
            self.listener = None
            return {"listener": False}
        # Lo arranco Windows al iniciar sesion, no esta ventana: no es nuestro para
        # matarlo, y quitar el arranque automatico es lo que de verdad se quiere.
        if self._listener_running():
            return {"listener": True, "ok": False, "error": "autostart"}
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


WINDOW_TITLE = "HotKeyConfig"   # nombre para la gente; el identificador es hotkeyconfig


def run(profile_path: str | Path) -> int:
    import os

    import webview

    from . import singleton, winfocus

    # Si ya hay un configurador abierto, se le devuelve al usuario ese y basta. Una
    # segunda ventana no serviria: se quedaria en blanco esperando la carpeta de
    # datos de WebView2, que es de una por usuario.
    if not singleton.claim():
        winfocus.raise_titled(WINDOW_TITLE, skip_pid=os.getpid())
        return 0

    # Turning off the HTTP cache: since the interface files sit next to the program,
    # WebView2 was serving the previous version of the interface after an update
    # while the Python side was already the new one. There is nothing to gain by
    # caching a handful of local files.
    os.environ.setdefault("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "--disable-http-cache")

    api = Api(profile_path)
    window = webview.create_window(
        WINDOW_TITLE, url=str(INDEX), js_api=api,
        width=900, height=710, min_size=(780, 600),
        background_color="#16161a",
    )

    api._window = window

    def on_closing() -> bool:
        """Do not let unsaved edits leave through the X without asking.

        The question is asked inside the interface (three plain answers, and in the
        chosen language) instead of with a system dialog, which on Windows only offers
        OK and Cancel: "Cancel" there could just as well mean "do not save" as "do not
        close". Asking runs on another thread because this one belongs to the window,
        and waiting here for the interface to answer would hang the close.

        If the interface never answers, a second click on the X closes anyway: better
        to lose the edits than to trap somebody inside a window that will not shut.
        """
        if not api.pending or api.close_asked:
            return True
        api.close_asked = True
        threading.Thread(target=lambda: window.evaluate_js("askClose()"),
                         daemon=True).start()
        return False

    window.events.closing += on_closing
    # private_mode=False so localStorage (language and so on) survives between sessions;
    # with the default private mode it was wiped on close. storage_path points at a
    # writable user folder (not the program directory, which can be read only).
    storage = os.path.join(os.environ.get("LOCALAPPDATA") or str(Path.home()), "hotkeyconfig", "webview")
    webview.start(private_mode=False, storage_path=storage, http_port=_free_port())
    return 0
