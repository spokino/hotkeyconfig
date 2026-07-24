"""Punto de entrada de PyInstaller.

Sin argumentos abre la ventana del configurador (doble clic en el .exe).
Cualquier subcomando (run, flash, detect, generate, autostart) pasa al CLI normal,
así el .exe se puede relanzar a sí mismo para el listener de fondo.
"""

import multiprocessing
import sys

from hotkeyconfig.cli import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    argv = sys.argv[1:]
    if not argv:
        argv = ["gui"]
    sys.exit(main(argv))
