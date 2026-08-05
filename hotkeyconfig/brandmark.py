"""The app logo, drawn in code, for the tray icon.

It is the same logo as ``branding/logo.svg``: the blue rounded square with the K
made of bars and dots. Drawn instead of loaded because ``branding/`` is not
packaged into the executable (``scripts/build.py`` only ships ``webui``), and the
tray needs an icon there too.

One deliberate difference: in the file the K is *cut out* of the square, so it is
transparent and takes the colour of whatever is behind. On a dark taskbar that
turns the logo into a blue square with black holes. Here the K is painted solid
white, so the icon looks the same on any theme.
"""

from __future__ import annotations

AZUL = (11, 79, 164, 255)      # #0B4FA4, el mismo del logo
BLANCO = (255, 255, 255, 255)

# Coordenadas del SVG original, sobre un lienzo de 100x100.
RADIO_CAJA = 16.0
BARRAS = ((14.30, 7.40, 3.70), (78.20, 7.40, 3.70))     # (x, ancho, radio)
CODOS = ((81.90, 20.50), (24.70, 49.50), (81.90, 78.40))
GROSOR_K = 7.40
PUNTOS = ((18.00, 20.50), (81.90, 20.50), (18.00, 78.40), (81.90, 78.40))
RADIO_PUNTO = 12.10


def draw_mark(size: int):
    """The logo on a square canvas of ``size`` pixels, with transparent corners."""
    from PIL import Image, ImageDraw

    # Se dibuja en grande y se reduce al final: es lo que suaviza los bordes, que a
    # 16 pixeles es la diferencia entre un logo y una mancha con dientes.
    escala = max(4, 512 // max(size, 1))
    lado = size * escala
    k = lado / 100.0

    base = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    ImageDraw.Draw(base).rounded_rectangle([0, 0, lado - 1, lado - 1],
                                           radius=RADIO_CAJA * k, fill=AZUL)

    marcas = Image.new("L", (lado, lado), 0)
    dibujo = ImageDraw.Draw(marcas)
    for x, ancho, radio in BARRAS:
        dibujo.rounded_rectangle([x * k, -2 * k, (x + ancho) * k, (100 + 2) * k],
                                 radius=radio * k, fill=255)
    grosor = max(1, round(GROSOR_K * k))
    dibujo.line([(x * k, y * k) for x, y in CODOS], fill=255, width=grosor, joint="curve")
    # joint="curve" redondea el vertice del medio, pero no las puntas: esas se
    # rematan a mano, como hace el stroke-linecap="round" del SVG.
    for x, y in (CODOS[0], CODOS[2]):
        r = grosor / 2
        dibujo.ellipse([x * k - r, y * k - r, x * k + r, y * k + r], fill=255)
    for x, y in PUNTOS:
        r = RADIO_PUNTO * k
        dibujo.ellipse([x * k - r, y * k - r, x * k + r, y * k + r], fill=255)

    # Las barras se salen del cuadrado por arriba y por abajo, igual que en el SVG:
    # el alfa del propio cuadrado las recorta para que no pinten fuera.
    recorte = Image.new("L", (lado, lado), 0)
    recorte.paste(marcas, (0, 0), base.getchannel("A"))
    base.paste(BLANCO, (0, 0), recorte)
    return base.resize((size, size), Image.LANCZOS)
