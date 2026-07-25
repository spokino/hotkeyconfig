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
        # `keyboard` lanza AttributeError si aún no hay listener (primer arranque).
        # unhook_all() limpia atajos Y remapeos previos (para recargar en caliente).
        try:
            keyboard.unhook_all()
        except (AttributeError, KeyError):
            pass
        self._registered = 0

        # 1) Controles del macropad (combos únicos F13-F24).
        for label, binding in self.profile.iter_bindings():
            action = binding.action
            if action.type in ("native", "unassigned"):
                continue
            self._register(keyboard, combos.to_keyboard(binding.combo), label, action)

        # 2) Atajos del teclado normal que el usuario grabó (formato de `keyboard`).
        for i, binding in enumerate(self.profile.hotkeys, start=1):
            if binding.action.type in ("unassigned", "native"):
                continue
            self._register(keyboard, binding.combo, f"atajo{i}", binding.action)

        # 3) Remapeos de teclas sueltas (tecla origen -> tecla destino).
        for r in self.profile.remaps:
            src, dst = r.get("from"), r.get("to")
            if not src or not dst:
                continue
            try:
                keyboard.remap_key(src, dst)
                self._registered += 1
            except Exception:  # noqa: BLE001
                log.exception("no pude remapear %s -> %s", src, dst)

        log.info("registrados %d atajos/remapeos desde %s", self._registered, self.profile_path)
        return self._registered

    def _register(self, keyboard, hotkey: str, label: str, action) -> None:
        try:
            keyboard.add_hotkey(
                hotkey, self._make_callback(label, action),
                suppress=True, trigger_on_release=False,
            )
            self._registered += 1
        except Exception:  # noqa: BLE001
            log.exception("no pude registrar %s (%s)", hotkey, label)

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

        try:
            keyboard.unhook_all()
        except (AttributeError, KeyError):
            pass
        log.info("runtime detenido")
