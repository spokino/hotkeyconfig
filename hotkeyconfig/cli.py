"""Command line interface: detect | generate | flash | run | gui | autostart."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from . import combos, flasher
from ._appcmd import is_frozen
from .profile import Action, Binding, Device, Layer, Profile, load, save


def _default_profile_path() -> Path:
    """Where profile.yaml lives: next to the code in development, in the user's data
    when the app is packaged (the program folder is read only)."""
    if is_frozen():
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "hotkeyconfig"
        return base / "profile.yaml"
    return Path(__file__).resolve().parent.parent / "config" / "profile.yaml"


DEFAULT_PROFILE = _default_profile_path()

# Default knob actions (native media, valid on any layer).
_DEFAULT_KNOBS = {
    0: {"ccw": "volume_down", "press": "mute", "cw": "volume_up"},
    1: {"ccw": "previous", "press": "play_pause", "cw": "next"},
}


def build_default_profile(device: Device | None = None) -> Profile:
    """Starting profile for a layout: unique combos, unassigned buttons, knobs on media."""
    device = device or Device()
    per_layer = device.rows * device.columns
    layers: list[Layer] = []
    for li in range(combos.LAYERS):
        buttons = [
            Binding(combos.button_combo(li, i, per_layer), Action("unassigned"))
            for i in range(per_layer)
        ]
        knobs: list[dict[str, Binding]] = []
        for ki in range(device.knobs):
            kd: dict[str, Binding] = {}
            for act in combos.KNOB_ACTIONS:
                combo = combos.knob_combo(li, ki, act, device.knobs)
                key = _DEFAULT_KNOBS.get(ki, {}).get(act)
                action = Action("native", {"key": key}) if key else Action("unassigned")
                kd[act] = Binding(combo, action)
            knobs.append(kd)
        layers.append(Layer(name=f"Layer {li + 1}", buttons=buttons, knobs=knobs))
    profile = Profile(device=device, layers=layers)
    profile.validate()
    return profile


# --- subcommands ---------------------------------------------------------
def cmd_detect(args: argparse.Namespace) -> int:
    from . import hid_flasher

    found = hid_flasher.detect()
    if found:
        print(f"[ok] keyboard {found['vid']:04x}:{found['pid']:04x} found "
              f"({found['family']} family, programming interface MI_00)")
        ok = True
    else:
        ok = False
        other = hid_flasher.detect_unsupported()
        if other:
            # Saying "not plugged in" here would be a lie and would send the user
            # chasing a cable that is fine.
            print(f"[warn] keyboard {other['vid']:04x}:{other['pid']:04x} found, but its "
                  f"{other['family']} protocol is not supported yet. Please report it at "
                  "https://github.com/Mun1to/hotkeyconfig/issues")
        else:
            print("[warn] cannot see any supported keyboard (is it plugged in?)")
    # The ch57x binary is OPTIONAL: HID flashing does not need it.
    try:
        print(f"[info] ch57x-keyboard-tool (optional): {flasher.find_binary()}")
    except flasher.FlasherError:
        print("[info] ch57x-keyboard-tool not installed (not needed for HID flashing)")
    return 0 if ok else 1


def cmd_generate(args: argparse.Namespace) -> int:
    out = Path(args.output)
    if out.exists() and not args.force:
        print(f"[error] {out} already exists. Use --force to overwrite.")
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    profile = build_default_profile()
    save(profile, out)
    n = sum(1 for _ in profile.iter_bindings())
    print(f"[ok] profile with {n} unique controls written to {out}")
    print("     Edit the button actions and then run: hotkeyconfig flash")
    return 0


def cmd_flash(args: argparse.Namespace) -> int:
    if not Path(args.profile).exists():
        print(f"[error] {args.profile} not found. Run this first: hotkeyconfig generate")
        return 1
    profile = load(args.profile)
    profile.validate()
    print(f"[..] mapping from {args.profile} validated ({sum(1 for _ in profile.iter_bindings())} controls)")

    if not args.yes:
        resp = input("This WRITES the configuration into the keyboard's memory. Continue? [y/N] ")
        if resp.strip().lower() not in ("y", "yes", "s", "si", "sí"):
            print("cancelled")
            return 1

    if args.backend == "ch57x":
        flasher.validate(profile)
        print("[..] writing through ch57x-keyboard-tool…")
        print(f"[ok] {flasher.flash(profile)}")
        return 0

    # Default backend: native HID (no Zadig, no drivers).
    from . import hid_flasher
    if hid_flasher.resolve(profile) is None:
        print("[error] cannot see the keyboard. Plug it in and retry (or use --backend ch57x).")
        return 1
    print("[..] writing over native HID…")
    n = hid_flasher.flash(profile)
    print(f"[ok] {n} messages written into the keyboard's memory (they persist without software)")
    return 0


def cmd_gui(args: argparse.Namespace) -> int:
    try:
        from . import gui_web
        return gui_web.run(args.profile)
    except ImportError:
        print("[warn] pywebview not available; opening the basic GUI (tkinter).")
        from . import gui
        return gui.run(args.profile)


def cmd_autostart(args: argparse.Namespace) -> int:
    from . import autostart

    if args.action == "status":
        if autostart.is_installed():
            print(f"[ok] autostart enabled: {autostart.shortcut_path()}")
        else:
            print("[info] autostart NOT installed")
        return 0
    if args.action == "install":
        profile = None if args.profile == str(DEFAULT_PROFILE) else args.profile
        path = autostart.install(profile)
        print(f"[ok] autostart installed: {path}")
        print("     The tray app will start on its own when you log into Windows.")
        return 0
    if args.action == "uninstall":
        removed = autostart.uninstall()
        print("[ok] autostart removed" if removed else "[info] it was not installed")
        return 0
    return 1


def _ensure_profile(path: str) -> None:
    """Create a default profile.yaml if missing (for example the first run after installing)."""
    p = Path(path)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        save(build_default_profile(), p)
        logging.getLogger("hotkeyconfig").info("default profile created at %s", p)


def cmd_run(args: argparse.Namespace) -> int:
    from .runtime import Runtime

    _ensure_profile(args.profile)
    runtime = Runtime(args.profile)
    if args.no_tray:
        runtime.load()
        try:
            runtime.run_forever()
        except KeyboardInterrupt:
            runtime.stop()
        return 0
    from .tray import run_tray
    run_tray(runtime)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hotkeyconfig",
        description="Program ch57x macropads and bind scripts and shortcuts to every key.",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="verbose logs")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("detect", help="check the tool and the device")

    g = sub.add_parser("generate", help="create a profile.yaml with unique combos")
    g.add_argument("-o", "--output", default=str(DEFAULT_PROFILE))
    g.add_argument("--force", action="store_true")

    f = sub.add_parser("flash", help="write the profile into the keyboard's memory")
    f.add_argument("-p", "--profile", default=str(DEFAULT_PROFILE))
    f.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    f.add_argument("--backend", choices=["hid", "ch57x"], default="hid",
                   help="hid (default, no drivers) or ch57x (external binary)")

    r = sub.add_parser("run", help="listen for the combos and run the actions")
    r.add_argument("-p", "--profile", default=str(DEFAULT_PROFILE))
    r.add_argument("--no-tray", action="store_true", help="no tray icon")

    gp = sub.add_parser("gui", help="visual configurator (click to bind actions)")
    gp.add_argument("-p", "--profile", default=str(DEFAULT_PROFILE))

    a = sub.add_parser("autostart", help="start automatically with Windows")
    a.add_argument("action", choices=["install", "uninstall", "status"])
    a.add_argument("-p", "--profile", default=str(DEFAULT_PROFILE))
    return p


_DISPATCH = {
    "detect": cmd_detect,
    "generate": cmd_generate,
    "flash": cmd_flash,
    "run": cmd_run,
    "gui": cmd_gui,
    "autostart": cmd_autostart,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    return _DISPATCH[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
