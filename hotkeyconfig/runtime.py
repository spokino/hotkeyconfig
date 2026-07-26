"""Runtime: listens for the unique combos and fires the actions.

Key design detail: because EVERY combo (across all layers) is unique, the runtime
never needs to track the active layer. The keyboard switches layer in hardware and
sends the matching combo; here each combo is just an independent global shortcut.
``native`` and ``unassigned`` actions are not registered.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from . import actions, combos
from .profile import Profile, load

log = logging.getLogger("hotkeyconfig.runtime")

# How long the keyboard keeps the colour of the control you pressed.
FEEDBACK_SECONDS = 0.5


def _layer_bindings(layer_idx: int, layer):
    """(label, Binding) of one layer, buttons first and then knob actions."""
    for bi, binding in enumerate(layer.buttons, start=1):
        yield (f"L{layer_idx + 1}/key{bi}", binding)
    for ki, knob in enumerate(layer.knobs, start=1):
        for act in combos.KNOB_ACTIONS:
            yield (f"L{layer_idx + 1}/knob{ki}/{act}", knob[act])


class Runtime:
    def __init__(self, profile_path: str | Path):
        self.profile_path = Path(profile_path)
        self.profile: Profile | None = None
        self.paused = False
        self._registered = 0
        self._restore_timer: threading.Timer | None = None

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
        for layer_idx, layer in enumerate(self.profile.layers):
            base = layer.led  # colour the layer goes back to after the feedback
            for label, binding in _layer_bindings(layer_idx, layer):
                action = binding.action
                if action.type in ("native", "unassigned"):
                    continue
                if binding.standalone:
                    # Windows takes care of this one through its own shortcut. It must
                    # not be registered here: the listener swallows what it registers,
                    # so the combo would never reach Explorer.
                    continue
                self._register(keyboard, combos.to_keyboard(binding.combo), label, action,
                               feedback=self._make_feedback(layer_idx, binding.color, base))

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

    def _make_feedback(self, layer_idx: int, color: str | None, base):
        """Flash the keyboard in ``color`` and go back to the layer colour.

        Returns None when there is nothing to do: without a colour on the control, or
        without lighting configured on the layer, there would be no base colour to
        return to. The ch57x cannot colour a single key, so the whole keyboard is
        tinted for a moment; see docs/PROTOCOL.md.
        """
        if not color or not base or not base.get("mode") or base.get("mode") == "keep":
            return None
        from . import hid_flasher

        def _flash() -> None:
            try:
                hid_flasher.set_led(color, layer=layer_idx)
                if self._restore_timer is not None:
                    self._restore_timer.cancel()

                def _restore() -> None:
                    try:
                        hid_flasher.set_led(base.get("color", "blue"),
                                            mode=base.get("mode", "backlight"),
                                            layer=layer_idx)
                    except Exception:  # noqa: BLE001 - lighting must never break an action
                        log.debug("could not restore the layer colour", exc_info=True)

                self._restore_timer = threading.Timer(FEEDBACK_SECONDS, _restore)
                self._restore_timer.daemon = True
                self._restore_timer.start()
            except Exception:  # noqa: BLE001
                log.debug("could not apply the press colour", exc_info=True)

        # In its own thread: writing to the keyboard takes about 20 ms and the action
        # should not wait for it.
        return lambda: threading.Thread(target=_flash, daemon=True).start()

    def _register(self, keyboard, hotkey: str, label: str, action, feedback=None) -> None:
        try:
            keyboard.add_hotkey(
                hotkey, self._make_callback(label, action, feedback),
                suppress=True, trigger_on_release=False,
            )
            self._registered += 1
        except Exception:  # noqa: BLE001
            log.exception("could not register %s (%s)", hotkey, label)

    def reload(self) -> int:
        log.info("reloading configuration…")
        return self.load()

    def _make_callback(self, label: str, action, feedback=None):
        def _cb():
            if self.paused:
                return
            log.debug("fired %s -> %s", label, action.type)
            if feedback is not None:
                feedback()
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
