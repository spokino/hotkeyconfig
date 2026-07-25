"""System tray icon, to drive the runtime without a terminal."""

from __future__ import annotations

import logging
import os
import threading

log = logging.getLogger("hotkeyconfig.tray")


def _make_icon_image():
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (64, 64), (24, 24, 28))
    draw = ImageDraw.Draw(img)
    # A minimal 3x4 grid that evokes the macropad.
    for r in range(3):
        for c in range(4):
            x, y = 8 + c * 13, 10 + r * 15
            draw.rounded_rectangle([x, y, x + 9, y + 11], radius=2, fill=(90, 140, 255))
    return img


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
