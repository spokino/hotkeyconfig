"""Genera el logo de hotkeyconfig: SVG vectorial con transparencia real + PNGs + .ico.

Lo blanco del diseño original NO se pinta: se recorta (knockout), así que el fondo
real se ve a través. Dos variantes:
  - logo-flush : fiel al original (barras hasta el borde)
  - logo       : ajustado, con margen interior -> aguanta fondo oscuro y recorte circular

Uso:  python scripts/make_logo.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "branding"
COLOR = (11, 79, 164)  # #0B4FA4 — el azul del logo
RADIUS = 16.0          # radio de esquina, en unidades de 0-100

# Geometría del símbolo (unidades 0-100), medida sobre el original.
# Las barras verticales pasan por el centro de los círculos; las diagonales
# unen los círculos derechos con un vértice sobre la barra izquierda (forma de K).
BAR_W = 7.4
BAR_X = (14.3, 78.2)          # x izquierda de cada barra vertical
CX = (18.0, 81.9)             # centros x (coinciden con el centro de las barras)
CY = (20.5, 78.4)             # centros y
CIRCLES = ((CX[0], CY[0]), (CX[1], CY[0]), (CX[0], CY[1]), (CX[1], CY[1]))
CIRCLE_R = 12.1
CHEVRON = ((CX[1], CY[0]), (24.7, 49.5), (CX[1], CY[1]))
STROKE = 7.4

INSET_SCALE = 0.86            # cuánto se encoge el símbolo en la variante ajustada
BAR_MARGIN = 9.0              # margen vertical de las barras en la variante ajustada


def _tx(pt, scale, cx=50.0, cy=50.0):
    """Escala un punto respecto al centro."""
    x, y = pt
    return (cx + (x - cx) * scale, cy + (y - cy) * scale)


def _shapes(inset: bool):
    """Devuelve las formas del símbolo (a recortar) en unidades 0-100."""
    s = INSET_SCALE if inset else 1.0
    bars, circles, chev = [], [], []
    for bx in BAR_X:
        x0, x1 = bx, bx + BAR_W
        y0, y1 = (BAR_MARGIN, 100.0 - BAR_MARGIN) if inset else (-1.0, 101.0)
        p0 = _tx((x0, y0), s)
        p1 = _tx((x1, y1), s)
        bars.append((p0[0], p0[1], p1[0], p1[1]))
    for c in CIRCLES:
        cx, cy = _tx(c, s)
        circles.append((cx, cy, CIRCLE_R * s))
    chev = [_tx(p, s) for p in CHEVRON]
    return bars, circles, chev, STROKE * s


# --- SVG -----------------------------------------------------------------
def build_svg(inset: bool) -> str:
    bars, circles, chev, stroke = _shapes(inset)
    hexcol = "#%02X%02X%02X" % COLOR
    rx = BAR_W * (INSET_SCALE if inset else 1.0) / 2
    parts = []
    for (x0, y0, x1, y1) in bars:
        parts.append(
            f'      <rect x="{x0:.2f}" y="{y0:.2f}" width="{x1 - x0:.2f}" '
            f'height="{y1 - y0:.2f}" rx="{rx:.2f}" fill="black"/>')
    d = " ".join(f'{"M" if i == 0 else "L"}{p[0]:.2f},{p[1]:.2f}' for i, p in enumerate(chev))
    parts.append(
        f'      <path d="{d}" fill="none" stroke="black" stroke-width="{stroke:.2f}" '
        f'stroke-linecap="round" stroke-linejoin="round"/>')
    for (cx, cy, r) in circles:
        parts.append(f'      <circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="black"/>')
    shapes = "\n".join(parts)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="512" height="512">
  <title>hotkeyconfig</title>
  <defs>
    <mask id="knockout">
      <rect width="100" height="100" fill="white"/>
{shapes}
    </mask>
  </defs>
  <rect width="100" height="100" rx="{RADIUS}" fill="{hexcol}" mask="url(#knockout)"/>
</svg>
"""


# --- PNG -----------------------------------------------------------------
def render_png(size: int, inset: bool, supersample: int = 8) -> Image.Image:
    n = size * supersample
    f = n / 100.0
    mask = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, n - 1, n - 1], radius=RADIUS * f, fill=255)

    bars, circles, chev, stroke = _shapes(inset)
    for (x0, y0, x1, y1) in bars:
        d.rounded_rectangle([x0 * f, y0 * f, x1 * f, y1 * f],
                            radius=(x1 - x0) * f / 2, fill=0)
    w = stroke * f
    d.line([(p[0] * f, p[1] * f) for p in chev], fill=0, width=int(round(w)), joint="curve")
    for p in chev:  # extremos redondeados
        d.ellipse([p[0] * f - w / 2, p[1] * f - w / 2, p[0] * f + w / 2, p[1] * f + w / 2], fill=0)
    for (cx, cy, r) in circles:
        d.ellipse([(cx - r) * f, (cy - r) * f, (cx + r) * f, (cy + r) * f], fill=0)

    img = Image.new("RGBA", (n, n), COLOR + (255,))
    img.putalpha(mask)
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # Principal = fiel al original (a sangre). La variante con margen queda aparte.
    (OUT / "logo.svg").write_text(build_svg(inset=False), encoding="utf-8")
    (OUT / "logo-safe.svg").write_text(build_svg(inset=True), encoding="utf-8")

    for size in (512, 256, 128, 64, 32, 16):
        render_png(size, inset=False).save(OUT / f"logo-{size}.png")
    render_png(256, inset=True).save(OUT / "logo-safe-256.png")

    icons = [render_png(s, inset=False) for s in (16, 32, 48, 64, 128, 256)]
    icons[-1].save(OUT / "favicon.ico", format="ICO",
                   sizes=[(i.width, i.height) for i in icons])

    print(f"[ok] logo generado en {OUT}")
    for p in sorted(OUT.iterdir()):
        print("   -", p.name)


if __name__ == "__main__":
    main()
