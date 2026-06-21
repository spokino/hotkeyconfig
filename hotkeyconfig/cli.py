"""Interfaz de línea de comandos: detect | generate | flash | run."""

from __future__ import annotations

import argparse
import logging
import subprocess
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
    try:
        binary = flasher.find_binary()
        print(f"[ok] ch57x-keyboard-tool: {binary}")
    except flasher.FlasherError as exc:
        print(f"[falta] {exc}")
        return 1
    # Detección del dispositivo en Windows por VID/PID.
    dev = Device()
    ps = (
        "Get-PnpDevice -PresentOnly | "
        f"Where-Object {{ $_.InstanceId -match 'VID_{dev.vid}' -and "
        f"$_.InstanceId -match 'PID_{dev.pid}' }} | "
        "Select-Object -ExpandProperty FriendlyName"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=15,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        out = ""
    if out:
        print(f"[ok] dispositivo {dev.vid}:{dev.pid} conectado -> {out}")
    else:
        print(f"[aviso] no veo el dispositivo {dev.vid}:{dev.pid} (¿enchufado?)")
    return 0


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
    print(f"[..] validando mapeo de {args.profile}")
    flasher.validate(profile)
    if not args.yes:
        resp = input("Esto ESCRIBIRÁ la configuración en el teclado. ¿Continuar? [s/N] ")
        if resp.strip().lower() not in ("s", "si", "sí", "y", "yes"):
            print("cancelado")
            return 1
    print("[..] grabando en el teclado…")
    out = flasher.flash(profile)
    print(f"[ok] {out}")
    return 0


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

    f = sub.add_parser("flash", help="graba el perfil en el teclado")
    f.add_argument("-p", "--profile", default=str(DEFAULT_PROFILE))
    f.add_argument("--yes", action="store_true", help="no preguntar confirmación")

    r = sub.add_parser("run", help="escucha los combos y ejecuta las acciones")
    r.add_argument("-p", "--profile", default=str(DEFAULT_PROFILE))
    r.add_argument("--no-tray", action="store_true", help="sin icono de bandeja")
    return p


_DISPATCH = {
    "detect": cmd_detect,
    "generate": cmd_generate,
    "flash": cmd_flash,
    "run": cmd_run,
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
