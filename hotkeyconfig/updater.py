"""Auto-actualización desde GitHub Releases (Windows).

Seguridad: solo se consulta y descarga del repositorio oficial por HTTPS, y solo
de hosts de GitHub. Si el release publica ``SHA256SUMS.txt``, se verifica el hash
del instalador ANTES de ejecutarlo. La app nunca descarga ni ejecuta nada de
fuentes externas.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from . import __version__

REPO = "Mun1to/hotkeyconfig"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
INSTALLER_SUFFIX = "-setup.exe"
CHECKSUMS_ASSET = "SHA256SUMS.txt"
USER_AGENT = f"hotkeyconfig/{__version__}"
ALLOWED_HOSTS = ("github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com")

_lock = threading.Lock()
_cache: dict | None = None


def _parse_version(text: str) -> tuple[int, int, int]:
    text = text.lstrip("vV").strip()
    parts: list[int] = []
    for chunk in text.split(".")[:3]:
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return parts[0], parts[1], parts[2]


def _request(url: str, accept: str | None = None) -> urllib.request.Request:
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    return urllib.request.Request(url, headers=headers)


def _host_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in ALLOWED_HOSTS or host.endswith(".githubusercontent.com")


def check_for_update(force: bool = False) -> dict:
    """Consulta el último release y compara con la versión actual (cacheado)."""
    global _cache
    with _lock:
        if _cache is not None and not force:
            return _cache
    result: dict = {"update_available": False, "current": __version__}
    try:
        req = _request(API_LATEST, accept="application/vnd.github+json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - sin conexión no es un error visible
        result["error"] = "no se pudo comprobar"
        with _lock:
            _cache = result
        return result

    latest_tag = data.get("tag_name", "")
    version = latest_tag.lstrip("vV")
    installer_url = None
    checksums_url = None
    for asset in data.get("assets", []):
        name = asset.get("name", "")
        url = asset.get("browser_download_url")
        # El release publica el instalador con la versión Y con un alias fijo;
        # nos quedamos con el versionado (canónico).
        if name.endswith(INSTALLER_SUFFIX):
            if installer_url is None or version in name:
                installer_url = url
        elif name == CHECKSUMS_ASSET:
            checksums_url = url

    frozen = bool(getattr(sys, "frozen", False))
    result.update({
        "update_available": _parse_version(latest_tag) > _parse_version(__version__),
        "latest": version,
        "notes_url": data.get("html_url"),
        "installer_url": installer_url,
        "checksums_url": checksums_url,
        "can_auto_install": bool(installer_url) and frozen and sys.platform == "win32",
    })
    with _lock:
        _cache = result
    return result


def _download(url: str, dst: Path) -> None:
    if not _host_allowed(url):
        raise ValueError(f"origen de descarga no permitido: {url}")
    with urllib.request.urlopen(_request(url), timeout=60) as resp, open(dst, "wb") as fh:
        while chunk := resp.read(65536):
            fh.write(chunk)


def _expected_sha256(checksums_url: str, filename: str) -> str | None:
    try:
        with urllib.request.urlopen(_request(checksums_url), timeout=20) as resp:
            for line in resp.read().decode("utf-8").splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1].lstrip("*") == filename:
                    return parts[0].lower()
    except Exception:  # noqa: BLE001
        return None
    return None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _quit_soon(delay: float = 1.2) -> None:
    """Cierra la app en segundo plano para que el instalador pueda reemplazarla."""
    def _quit() -> None:
        import time
        time.sleep(delay)
        os._exit(0)
    threading.Thread(target=_quit, daemon=True).start()


def apply_update() -> dict:
    """Descarga el instalador, verifica el hash y lo lanza en silencioso."""
    info = check_for_update()
    url = info.get("installer_url")
    if not url or not info.get("can_auto_install"):
        return {"ok": False, "error": "actualización automática no disponible"}
    if not _host_allowed(url):
        return {"ok": False, "error": "origen de descarga no confiable"}

    asset_name = url.rsplit("/", 1)[-1]
    dst = Path(tempfile.gettempdir()) / asset_name
    try:
        _download(url, dst)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"fallo al descargar: {exc}"}

    if info.get("checksums_url"):
        expected = _expected_sha256(info["checksums_url"], asset_name)
        if expected and _sha256(dst) != expected:
            dst.unlink(missing_ok=True)
            return {"ok": False, "error": "el checksum no coincide; descarga abortada"}

    try:
        subprocess.Popen([str(dst), "/SILENT", "/NORESTART", "/SUPPRESSMSGBOXES"], close_fds=True)
    except OSError as exc:
        return {"ok": False, "error": f"no se pudo iniciar el instalador: {exc}"}
    _quit_soon()
    return {"ok": True}
