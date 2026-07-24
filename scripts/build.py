"""Empaqueta hotkeyconfig como .exe (PyInstaller) e instalador (Inno Setup).

Uso:
    python scripts/build.py              # solo el .exe -> dist/hotkeyconfig/
    python scripts/build.py --installer  # además dist/hotkeyconfig-<version>-setup.exe

Convención (igual que Expoal): dist/, build/ y *.spec no se versionan; este script
y installer/hotkeyconfig.iss sí. La versión sale de hotkeyconfig/__init__.py.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_version() -> str:
    text = (ROOT / "hotkeyconfig" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not m:
        raise SystemExit("no encuentro __version__ en hotkeyconfig/__init__.py")
    return m.group(1)


def build_exe() -> None:
    import PyInstaller.__main__

    sep = ";" if os.name == "nt" else ":"
    args = [
        str(ROOT / "launcher.py"),
        "--name", "hotkeyconfig",
        "--noconfirm",
        "--clean",
        "--windowed",  # sin consola (console=False)
        "--icon", str(ROOT / "branding" / "favicon.ico"),
        "--add-data", f"{ROOT / 'hotkeyconfig' / 'webui'}{sep}hotkeyconfig/webui",
        "--collect-all", "webview",   # pywebview + WebView2Loader.dll
        "--collect-all", "hid",       # DLL de hidapi
        "--collect-submodules", "pystray",
        "--hidden-import", "pystray._win32",
        "--hidden-import", "win32timezone",
        "--hidden-import", "clr",     # pythonnet (backend winforms de pywebview)
        "--workpath", str(ROOT / "build"),
        "--distpath", str(ROOT / "dist"),
        "--specpath", str(ROOT),
    ]
    PyInstaller.__main__.run(args)
    print(f"[ok] .exe en {ROOT / 'dist' / 'hotkeyconfig' / 'hotkeyconfig.exe'}")


def build_installer(version: str) -> None:
    iscc = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Inno Setup 6" / "ISCC.exe"
    if not iscc.exists():
        raise SystemExit(f"no encuentro ISCC (Inno Setup 6) en {iscc}")
    subprocess.run(
        [str(iscc), f"/DMyAppVersion={version}", str(ROOT / "installer" / "hotkeyconfig.iss")],
        cwd=ROOT, check=True,
    )
    print(f"[ok] instalador en {ROOT / 'dist' / f'hotkeyconfig-{version}-setup.exe'}")


def main() -> None:
    version = read_version()
    print(f"== hotkeyconfig {version} ==")
    build_exe()
    if "--installer" in sys.argv:
        build_installer(version)


if __name__ == "__main__":
    main()
