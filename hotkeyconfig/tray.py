"""Icono en la bandeja del sistema para controlar el runtime sin terminal."""

from __future__ import annotations

import logging
import os
import threading

log = logging.getLogger("hotkeyconfig.tray")


def _make_icon_image():
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (64, 64), (24, 24, 28))
    draw = ImageDraw.Draw(img)
    # Una rejilla 3x4 minimalista que evoca el macropad.
    for r in range(3):
        for c in range(4):
            x, y = 8 + c * 13, 10 + r * 15
            draw.rounded_rectangle([x, y, x + 9, y + 11], radius=2, fill=(90, 140, 255))
    return img


def run_tray(runtime) -> None:
    """Arranca el listener en un hilo y muestra el icono de bandeja (bloquea)."""
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
            icon.notify(f"Recargado: {n} atajos activos", "hotkeyconfig")
        except Exception as exc:  # noqa: BLE001
            icon.notify(f"Error al recargar: {exc}", "hotkeyconfig")

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
        Item("Abrir configurador", on_gui, default=True),
        Item(
            lambda item: "Reanudar" if runtime.paused else "Pausar",
            on_toggle,
        ),
        Item("Recargar configuracion", on_reload),
        Item("Editar profile.yaml", on_edit),
        pystray.Menu.SEPARATOR,
        Item("Salir", on_quit),
    )
    icon = pystray.Icon("hotkeyconfig", _make_icon_image(), "hotkeyconfig", menu)
    icon.run()
