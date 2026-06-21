"""Runtime: escucha los combos únicos y dispara las acciones.

Detalle clave del diseño: como TODOS los combos (las 3 capas) son únicos, el
runtime no necesita seguir el estado de capa. El teclado conmuta de capa por
hardware y envía el combo correspondiente; aquí cada combo es un atajo global
independiente. Las acciones ``native``/``unassigned`` no se registran.
"""

from __future__ import annotations

import logging
from pathlib import Path

from . import actions, combos
from .profile import Profile, load

log = logging.getLogger("hotkeyconfig.runtime")


class Runtime:
    def __init__(self, profile_path: str | Path):
        self.profile_path = Path(profile_path)
        self.profile: Profile | None = None
        self.paused = False
        self._registered = 0

    # --- ciclo de vida ---------------------------------------------------
    def load(self) -> int:
        """(Re)carga el perfil y registra los atajos. Devuelve cuántos registró."""
        import keyboard

        combos.assert_unique()
        self.profile = load(self.profile_path)
        keyboard.unhook_all_hotkeys()
        self._registered = 0
        for label, binding in self.profile.iter_bindings():
            action = binding.action
            if action.type in ("native", "unassigned"):
                continue
            hotkey = combos.to_keyboard(binding.combo)
            try:
                keyboard.add_hotkey(
                    hotkey,
                    self._make_callback(label, action),
                    suppress=True,
                    trigger_on_release=False,
                )
                self._registered += 1
            except Exception:  # noqa: BLE001
                log.exception("no pude registrar %s (%s)", hotkey, label)
        log.info("registrados %d atajos desde %s", self._registered, self.profile_path)
        return self._registered

    def reload(self) -> int:
        log.info("recargando configuracion…")
        return self.load()

    def _make_callback(self, label: str, action):
        def _cb():
            if self.paused:
                return
            log.debug("disparo %s -> %s", label, action.type)
            actions.execute(action)
        return _cb

    def set_paused(self, value: bool) -> None:
        self.paused = value
        log.info("runtime %s", "en pausa" if value else "activo")

    def run_forever(self) -> None:
        """Bloquea el hilo actual escuchando hasta que se pulse ESC+salir o se cierre."""
        import keyboard

        if self.profile is None:
            self.load()
        log.info("hotkeyconfig en marcha (%d atajos). Ctrl+C para salir.", self._registered)
        keyboard.wait()  # bloquea indefinidamente

    def stop(self) -> None:
        import keyboard

        keyboard.unhook_all_hotkeys()
        log.info("runtime detenido")
