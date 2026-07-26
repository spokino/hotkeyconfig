"""Genera las capturas de pantalla del README (ES e EN).

Abre la GUI real con un perfil de DEMOSTRACION (nunca toca el perfil del usuario),
la lleva a cada pantalla por JavaScript y captura la ventana. Asi las capturas se
pueden regenerar de forma reproducible cuando cambie la interfaz:

    .venv\\Scripts\\python scripts/screenshots.py

Salida: branding/screenshots/<lang>/NN-<nombre>.png
"""

from __future__ import annotations

import ctypes
import os
import sys
import tempfile
import threading
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import webview  # noqa: E402
from PIL import ImageChops, ImageGrab  # noqa: E402

from hotkeyconfig import gui_web, winfocus  # noqa: E402
from hotkeyconfig.cli import build_default_profile  # noqa: E402
from hotkeyconfig.profile import Action, Binding, save  # noqa: E402

OUT = ROOT / "branding" / "screenshots"
WIDTH, HEIGHT = 1060, 760
SETTLE = 0.5  # margen para que pinte la interfaz antes de capturar


# --- perfil de demostracion ------------------------------------------------
def demo_profile():
    """Perfil de ejemplo con acciones variadas (para que la captura sea util)."""
    prof = build_default_profile()
    demo = [
        ("open", {"target": "spotify:"}),
        ("run", {"cmd": "py C:/scripts/deploy.py"}),
        ("text", {"text": "hola@ejemplo.com"}),
        ("hotkey", {"send": "ctrl+shift+s"}),
        ("open", {"target": "https://github.com/Mun1to"}),
        ("media", {"key": "play_pause"}),
        ("window", {"do": "minimize"}),
        ("run", {"cmd": "pwsh C:/scripts/backup.ps1"}),
    ]
    colores = ["green", "purple", "cyan", "orange", None, None, None, "red"]
    layer = prof.layers[0]
    for i, (type_, params) in enumerate(demo):
        if i < len(layer.buttons):
            layer.buttons[i].action = Action(type=type_, params=params)
            layer.buttons[i].color = colores[i]
    layer.led = {"mode": "backlight", "color": "blue"}

    prof.hotkeys = [
        Binding(combo="ctrl+alt+s", action=Action("run", {"cmd": "py C:/scripts/screenshot.py"})),
        Binding(combo="ctrl+alt+d", action=Action("open", {"target": "C:/proyectos"})),
    ]
    prof.remaps = [{"from": "caps lock", "to": "esc"}]
    return prof


# --- captura de la ventana propia ------------------------------------------
user32, dwmapi = ctypes.windll.user32, ctypes.windll.dwmapi
DWMWA_EXTENDED_FRAME_BOUNDS = 9


def own_hwnd() -> int:
    """HWND de la ventana visible de ESTE proceso (evita capturar otra instancia)."""
    found = []
    pid_here = os.getpid()

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _lparam):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == pid_here and user32.IsWindowVisible(hwnd):
            if user32.GetWindowTextLengthW(hwnd) > 0:
                found.append(hwnd)
        return True

    user32.EnumWindows(cb, 0)
    return found[0] if found else 0


def window_box(hwnd: int):
    """Rectangulo real del marco (sin la sombra), en pixeles de pantalla."""
    rect = wintypes.RECT()
    if dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd), ctypes.c_uint(DWMWA_EXTENDED_FRAME_BOUNDS),
        ctypes.byref(rect), ctypes.sizeof(rect),
    ) != 0:
        user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect))
    return (rect.left, rect.top, rect.right, rect.bottom)


def bring_to_front(hwnd: int, move_to=None) -> None:
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    if move_to:  # colocar en una zona despejada del monitor principal
        user32.SetWindowPos(hwnd, wintypes.HWND(-1), move_to[0], move_to[1], 0, 0,
                            0x0001 | 0x0040)  # SWP_NOSIZE | SWP_SHOWWINDOW
    else:
        user32.SetWindowPos(hwnd, wintypes.HWND(-1), 0, 0, 0, 0, 0x0001 | 0x0002)
    # SetForegroundWindow a secas no basta: Windows se lo deniega a un proceso que
    # no tiene ya el primer plano, y entonces otra ventana puede quedar por delante
    # y la calibracion no encuentra la app. winfocus sabe insistir de la unica forma
    # que funciona (una entrada sintetica minima antes de pedirlo).
    winfocus._raise(hwnd)
    time.sleep(0.25)


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def assert_unobstructed(hwnd: int, box) -> None:
    """Aborta si CUALQUIER otra ventana tapa la nuestra.

    WebView2 compone por GPU y no se puede volcar con PrintWindow, asi que hay que
    leer de la pantalla. Para que la captura no pueda recoger nada ajeno (podria ser
    informacion privada del usuario), se comprueba antes que cada punto del recuadro
    pertenece a esta ventana.
    """
    left, top, right, bottom = box
    xs = [left, left + (right - left) // 2, right - 1]
    ys = [top, top + (bottom - top) // 2, bottom - 1]
    for px in xs:
        for py in ys:
            owner = user32.GetAncestor(user32.WindowFromPoint(POINT(px, py)), 2)  # GA_ROOT
            if owner != hwnd:
                raise RuntimeError(
                    f"otra ventana tapa la app en ({px},{py}): capturar leeria "
                    "contenido ajeno")


def client_box(hwnd: int):
    """Rectangulo del area de contenido (sin marco) en coordenadas de pantalla."""
    rect = wintypes.RECT()
    user32.GetClientRect(wintypes.HWND(hwnd), ctypes.byref(rect))
    origin = POINT(0, 0)
    user32.ClientToScreen(wintypes.HWND(hwnd), ctypes.byref(origin))
    return (origin.x, origin.y, origin.x + rect.right, origin.y + rect.bottom)


def _dominant_run(mask, axis: str):
    """Franja contigua con mas marca a lo largo de un eje.

    Se queda con el bloque dominante en vez del rectangulo que engloba todo: un
    pixel suelto del mismo color en otra parte de la pantalla falsearia la medida.
    """
    w, h = mask.size
    # Proyeccion del eje: media por fila (o por columna), calculada por PIL.
    line = mask.resize((1, h)) if axis == "y" else mask.resize((w, 1))
    values = list(line.tobytes())
    peak = max(values)
    if peak == 0:
        raise RuntimeError("calibracion fallida: marca no visible")
    limit = peak * 0.5
    best = values.index(peak)
    start = best
    while start > 0 and values[start - 1] >= limit:
        start -= 1
    end = best
    while end < len(values) - 1 and values[end + 1] >= limit:
        end += 1
    return start, end + 1


def calibrate(window, hwnd: int):
    """Deduce la transformacion pantalla -> imagen pintando la app de un color unico.

    Evita adivinar el escalado DPI y el origen del escritorio virtual: se mide.
    Devuelve (escala_x, escala_y, desplazamiento_x, desplazamiento_y).
    """
    # Color raro y coincidencia EXACTA: cualquier otro pixel parecido en pantalla
    # falsearia el rectangulo detectado.
    mark = (254, 0, 253)
    window.evaluate_js(
        "(function(){var d=document.createElement('div');d.id='__cal';"
        f"d.style.cssText='position:fixed;inset:0;background:rgb({mark[0]},{mark[1]},{mark[2]});"
        "z-index:99999';document.body.appendChild(d);})(); ''")
    time.sleep(0.45)
    full = ImageGrab.grab(all_screens=True)
    window.evaluate_js("document.getElementById('__cal').remove(); ''")

    # Tolerancia pequena: distintos monitores devuelven el color con leves variaciones.
    tol = 10
    red, green, blue = full.convert("RGB").split()
    hot = ImageChops.multiply(
        ImageChops.multiply(red.point(lambda v: 255 if abs(v - mark[0]) <= tol else 0),
                            green.point(lambda v: 255 if abs(v - mark[1]) <= tol else 0)),
        blue.point(lambda v: 255 if abs(v - mark[2]) <= tol else 0))
    if not hot.getbbox():
        # Con el dato de donde deberia estar la ventana se ve enseguida si el
        # problema es que quedo tapada, minimizada o fuera de la pantalla.
        raise RuntimeError(
            "calibracion fallida: no localizo la ventana en la pantalla. "
            f"La app dice estar en {window_box(hwnd)} y la captura mide {full.size}")
    found = (*_dominant_run(hot, "x"), *_dominant_run(hot, "y"))
    found = (found[0], found[2], found[1], found[3])

    cx0, cy0, cx1, cy1 = client_box(hwnd)
    sx = (found[2] - found[0]) / (cx1 - cx0)
    sy = (found[3] - found[1]) / (cy1 - cy0)
    # Una captura de pantalla nunca deforma distinto en cada eje: si pasa, lo detectado
    # no es la ventana y seguir produciria imagenes con contenido ajeno.
    if abs(sx - sy) > 0.01:
        raise RuntimeError(f"calibracion incoherente (escala {sx:.3f}x{sy:.3f})")
    return sx, sy, found[0] - cx0 * sx, found[1] - cy0 * sy


def capture(hwnd: int, path: Path, cal) -> None:
    box = window_box(hwnd)
    assert_unobstructed(hwnd, box)
    sx, sy, ox, oy = cal
    # Margen hacia dentro: las esquinas redondeadas de Windows 11 dejan ver el
    # escritorio en el borde, y ahi se colaria contenido de otras ventanas.
    inset = 5
    bbox = (round(box[0] * sx + ox) + inset, round(box[1] * sy + oy) + inset,
            round(box[2] * sx + ox) - inset, round(box[3] * sy + oy) - inset)
    img = ImageGrab.grab(all_screens=True).crop(bbox)

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    print(f"  {path.relative_to(ROOT)}  {img.width}x{img.height}", flush=True)


# --- guion de las capturas -------------------------------------------------
# (nombre de archivo, JS que deja la interfaz en el estado deseado)
SHOTS = [
    ("01-macropad", "switchSection('pad'); state.layer=0; renderAll(); ''"),
    # Editor abierto SIN desplegar el tipo: asi se ve el campo de color al pulsar,
    # que quedaria tapado por el menu.
    ("02-editor", "switchSection('pad'); document.querySelector('.grid .key').click(); ''"),
    ("03-shortcuts", "closeEditor(); switchSection('keys'); ''"),
    ("04-guide", "switchSection('guide'); ''"),
    # El catalogo de teclados desplegado: es lo que responde a "¿vale para el mio?".
    ("05-models", "switchSection('pad'); $('lbModel')._enh.trigger.click(); ''"),
]


def run_shots(window) -> None:
    for _ in range(60):  # esperar a que init() termine
        time.sleep(0.25)
        try:
            if window.evaluate_js("document.querySelectorAll('.grid .key').length > 0"):
                break
        except Exception:  # noqa: BLE001
            pass

    hwnd = own_hwnd()
    if not hwnd:
        print("ERROR: no encuentro la ventana propia", flush=True)
        return
    # Zona despejada: barras y paneles suelen vivir pegados a los bordes.
    bring_to_front(hwnd, move_to=(120, 90))
    time.sleep(0.4)
    cal = calibrate(window, hwnd)
    print(f"calibracion: escala {cal[0]:.3f}x{cal[1]:.3f}, origen {cal[2]:.0f},{cal[3]:.0f}",
          flush=True)

    for lang in ("es", "en"):
        print(f"[{lang}]", flush=True)
        window.evaluate_js(f"applyLang('{lang}'); ''")
        time.sleep(0.35)
        for name, js in SHOTS:
            window.evaluate_js(js)
            time.sleep(SETTLE)
            bring_to_front(hwnd)
            capture(hwnd, OUT / lang / f"{name}.png", cal)
        window.evaluate_js("closeAllMenus(); closeEditor(); switchSection('pad'); ''")
        time.sleep(0.2)


def main() -> None:
    tmp = Path(tempfile.gettempdir()) / "hotkeyconfig-demo-profile.yaml"
    save(demo_profile(), tmp)

    api = gui_web.Api(tmp)
    window = webview.create_window(
        "HotKeyConfig", url=str(gui_web.INDEX), js_api=api,   # el mismo titulo que la app
        width=WIDTH, height=HEIGHT, background_color="#16161a",
    )

    def worker():
        try:
            run_shots(window)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: {exc!r}", flush=True)
        finally:
            try:
                window.destroy()
            except Exception:  # noqa: BLE001
                pass
            tmp.unlink(missing_ok=True)
            os._exit(0)

    # Red de seguridad: nunca dejar el proceso colgado.
    threading.Thread(target=lambda: (time.sleep(120), os._exit(1)), daemon=True).start()
    # Puerto propio: pywebview sirve la interfaz por HTTP en uno fijo y, si esta
    # ocupado, carga la de la otra instancia. Sin esto las capturas pueden salir
    # de una version antigua del programa que estuviera abierta.
    webview.start(worker, http_port=gui_web._free_port())


if __name__ == "__main__":
    main()
