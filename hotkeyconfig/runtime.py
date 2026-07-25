"""Runtime: listens for the unique combos and fires the actions.

Key design detail: because EVERY combo (across all layers) is unique, the runtime
never needs to track the active layer. The keyboard switches layer in hardware and
sends the matching combo; here each combo is just an independent global shortcut.
``native`` and ``unassigned`` actions are not registered.
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

    # --- lifecycle -------------------------------------------------------
    def load(self) -> int:
        """(Re)load the profile and register the shortcuts. Returns how many were registered."""
        import keyboard

        combos.assert_unique()
        self.profile = load(self.profile_path)
        # `keyboard` raises AttributeError when there is no listener yet (first run).
        # unhook_all() clears previous shortcuts AND remaps (so reloading works hot).
        try:
            keyboard.unhook_all()
        except (AttributeError, KeyError):
            pass
        self._registered = 0

        # 1) Macropad controls (the unique F13 to F24 combos).
        for label, binding in self.profile.iter_bindings():
            action = binding.action
            if action.type in ("native", "unassigned"):
                continue
            self._register(keyboard, combos.to_keyboard(binding.combo), label, action)

        # 2) Normal keyboard shortcuts recorded by the user (`keyboard` format).
        for i, binding in enumerate(self.profile.hotkeys, start=1):
            if binding.action.type in ("unassigned", "native"):
                continue
            self._register(keyboard, binding.combo, f"shortcut{i}", binding.action)

        # 3) Single key remaps (source key -> target key).
        for r in self.profile.remaps:
            src, dst = r.get("from"), r.get("to")
            if not src or not dst:
                continue
            try:
                keyboard.remap_key(src, dst)
                self._registered += 1
            except Exception:  # noqa: BLE001
                log.exception("could not remap %s -> %s", src, dst)

        log.info("registered %d shortcuts/remaps from %s", self._registered, self.profile_path)
        return self._registered

    def _register(self, keyboard, hotkey: str, label: str, action) -> None:
        try:
            keyboard.add_hotkey(
                hotkey, self._make_callback(label, action),
                suppress=True, trigger_on_release=False,
            )
            self._registered += 1
        except Exception:  # noqa: BLE001
            log.exception("could not register %s (%s)", hotkey, label)

    def reload(self) -> int:
        log.info("reloading configuration…")
        return self.load()

    def _make_callback(self, label: str, action):
        def _cb():
            if self.paused:
                return
            log.debug("fired %s -> %s", label, action.type)
            actions.execute(action)
        return _cb

    def set_paused(self, value: bool) -> None:
        self.paused = value
        log.info("runtime %s", "paused" if value else "active")

    def run_forever(self) -> None:
        """Block the current thread, listening until the process is stopped."""
        import keyboard

        if self.profile is None:
            self.load()
        log.info("hotkeyconfig running (%d shortcuts). Ctrl+C to quit.", self._registered)
        keyboard.wait()  # blocks indefinitely

    def stop(self) -> None:
        import keyboard

        try:
            keyboard.unhook_all()
        except (AttributeError, KeyError):
            pass
        log.info("runtime stopped")
