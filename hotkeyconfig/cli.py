"""Interfaz de línea de comandos: detect | generate | flash | run."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import combos, flasher
from .profile import Action, Binding, Device, Layer, Profile, load, save

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE = PROJECT_ROOT / "config" / "profile.yaml"

# Acciones por defecto de las perillas (multimedia nativo, válido en cualquier capa).
_DEFAULT_KNOBS = {
    0: {"ccw": "volume_down", "press": "mute", "cw": "volume_up"},
    1: {"ccw": "previous", "press": "play_pause", "cw": "next"},
}


def build_default_profile() -> Profile:
    """Perfil inicial: combos únicos en todo, botones sin asignar, perillas a multimedia."""
    device = Device()
    layers: list[Layer] = []
    for li in range(combos.LAYERS):
        buttons = [
            Binding(combos.button_combo(li, i), Action("unassigned"))
            for i in range(device.rows * device.columns)
        ]
        knobs: list[dict[str, Binding]] = []
        for ki in range(device.knobs):
            kd: dict[str, Binding] = {}
            for act in combos.KNOB_ACTIONS:
                combo = combos.knob_combo(li, ki, act)
                key = _DEFAULT_KNOBS.get(ki, {}).get(act)
                action = Action("native", {"key": key}) if key else Action("unassigned")
                kd[act] = Binding(combo, action)
            knobs.append(kd)
        layers.append(Layer(name=f"Capa {li + 1}", buttons=buttons, knobs=knobs))
    profile = Profile(device=device, layers=layers)
    profile.validate()
    return profile


# --- subcomandos ---------------------------------------------------------
def cmd_detect(args: argparse.Namespace) -> int:
    from . import hid_flasher

    dev = Device()
    if hid_flasher.is_connected():
        print(f"[ok] teclado {dev.vid}:{dev.pid} detectado (interfaz de programacion MI_00)")
        ok = True
    else:
        print(f"[aviso] no veo el teclado {dev.vid}:{dev.pid} (¿enchufado?)")
        ok = False
    # El binario de ch57x es OPCIONAL: el flasheo por HID no lo necesita.
    try:
        print(f"[info] ch57x-keyboard-tool (opcional): {flasher.find_binary()}")
    except flasher.FlasherError:
        print("[info] ch57x-keyboard-tool no instalado (no hace falta para el flasheo HID)")
    return 0 if ok else 1


def cmd_generate(args: argparse.Namespace) -> int:
    out = Path(args.output)
    if out.exists() and not args.force:
        print(f"[error] {out} ya existe. Usa --force para sobrescribir.")
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    profile = build_default_profile()
    save(profile, out)
    n = sum(1 for _ in profile.iter_bindings())
    print(f"[ok] perfil con {n} controles únicos escrito en {out}")
    print("     Edita las acciones de los botones y luego: hotkeyconfig flash")
    return 0


def cmd_flash(args: argparse.Namespace) -> int:
    profile = load(args.profile)
    profile.validate()
    print(f"[..] mapeo de {args.profile} validado ({sum(1 for _ in profile.iter_bindings())} controles)")

    if not args.yes:
        resp = input("Esto ESCRIBIRÁ la configuración en la memoria del teclado. ¿Continuar? [s/N] ")
        if resp.strip().lower() not in ("s", "si", "sí", "y", "yes"):
            print("cancelado")
            return 1

    if args.backend == "ch57x":
        flasher.validate(profile)
        print("[..] grabando por ch57x-keyboard-tool…")
        print(f"[ok] {flasher.flash(profile)}")
        return 0

    # Backend por defecto: HID nativo (sin Zadig ni drivers).
    from . import hid_flasher
    if not hid_flasher.is_connected():
        print("[error] no veo el teclado. Conéctalo y reintenta (o usa --backend ch57x).")
        return 1
    print("[..] grabando por HID nativo…")
    n = hid_flasher.flash(profile)
    print(f"[ok] {n} mensajes grabados en la memoria del teclado (persisten sin software)")
    return 0


def cmd_gui(args: argparse.Namespace) -> int:
    try:
        from . import gui_web
        return gui_web.run(args.profile)
    except ImportError:
        print("[aviso] pywebview no disponible; abriendo la GUI básica (tkinter).")
        from . import gui
        return gui.run(args.profile)


def cmd_autostart(args: argparse.Namespace) -> int:
    from . import autostart

    if args.action == "status":
        if autostart.is_installed():
            print(f"[ok] arranque automático activo: {autostart.shortcut_path()}")
        else:
            print("[info] arranque automático NO instalado")
        return 0
    if args.action == "install":
        profile = None if args.profile == str(DEFAULT_PROFILE) else args.profile
        path = autostart.install(profile)
        print(f"[ok] arranque automático instalado: {path}")
        print("     La app de bandeja se iniciará sola al entrar en Windows.")
        return 0
    if args.action == "uninstall":
        removed = autostart.uninstall()
        print("[ok] arranque automático eliminado" if removed else "[info] no estaba instalado")
        return 0
    return 1


def cmd_run(args: argparse.Namespace) -> int:
    from .runtime import Runtime

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
        description="Programa macropads ch57x y asígnales scripts/atajos.",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="logs detallados")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("detect", help="comprueba la herramienta y el dispositivo")

    g = sub.add_parser("generate", help="crea un profile.yaml con combos únicos")
    g.add_argument("-o", "--output", default=str(DEFAULT_PROFILE))
    g.add_argument("--force", action="store_true")

    f = sub.add_parser("flash", help="graba el perfil en la memoria del teclado")
    f.add_argument("-p", "--profile", default=str(DEFAULT_PROFILE))
    f.add_argument("--yes", action="store_true", help="no preguntar confirmación")
    f.add_argument("--backend", choices=["hid", "ch57x"], default="hid",
                   help="hid (por defecto, sin drivers) o ch57x (binario externo)")

    r = sub.add_parser("run", help="escucha los combos y ejecuta las acciones")
    r.add_argument("-p", "--profile", default=str(DEFAULT_PROFILE))
    r.add_argument("--no-tray", action="store_true", help="sin icono de bandeja")

    gp = sub.add_parser("gui", help="configurador gráfico (clic para asignar acciones)")
    gp.add_argument("-p", "--profile", default=str(DEFAULT_PROFILE))

    a = sub.add_parser("autostart", help="arranque automático con Windows")
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
