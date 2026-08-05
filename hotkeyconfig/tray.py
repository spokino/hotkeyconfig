"""System tray icon, to drive the runtime without a terminal."""

from __future__ import annotations

import logging
import os
import threading

log = logging.getLogger("hotkeyconfig.tray")


def _make_icon_image():
    """The app logo, the same one the executable and the installer wear.

    It used to be a 3x4 grid of blue rectangles drawn here, which was the only
    place with a different drawing. Asked for at 32 pixels, which is what Windows
    wants for the tray: drawing it bigger and letting the system shrink it blurs
    the dots and the bars.
    """
    from . import brandmark

    return brandmark.draw_mark(32)


def run_tray(runtime) -> None:
    """Start the listener on a thread and show the tray icon (blocks)."""
    import pystray
    from pystray import MenuItem as Item

    runtime.load()
    listener = threading.Thread(target=runtime.run_forever, daemon=True)
    listener.start()

    def on_toggle(icon, item):
        runtime.set_paused(not runtime.paused)

    def on_reload(icon, item):
        try:
            n = runtime.reload()
            icon.notify(f"Reloaded: {n} shortcuts active", "hotkeyconfig")
        except Exception as exc:  # noqa: BLE001
            icon.notify(f"Reload failed: {exc}", "hotkeyconfig")

    def on_gui(icon, item):
        import subprocess

        from ._appcmd import app_command
        subprocess.Popen(app_command("gui", "-p", str(runtime.profile_path)))

    def on_edit(icon, item):
        os.startfile(str(runtime.profile_path))  # type: ignore[attr-defined]

    def on_quit(icon, item):
        runtime.stop()
        icon.stop()

    menu = pystray.Menu(
        Item("Open configurator", on_gui, default=True),
        Item(
            lambda item: "Resume" if runtime.paused else "Pause",
            on_toggle,
        ),
        Item("Reload configuration", on_reload),
        Item("Edit profile.yaml", on_edit),
        pystray.Menu.SEPARATOR,
        Item("Quit", on_quit),
    )
    icon = pystray.Icon("hotkeyconfig", _make_icon_image(), "hotkeyconfig", menu)
    icon.run()
