"""Installed applications, the same list the Start menu shows (Windows only).

Typing a path by hand is the worst part of setting up a key: nobody remembers
where Spotify lives, and Store apps have no path at all. Windows already keeps
the answer in the shell's ``AppsFolder``, the virtual folder behind the Start
menu, which covers Win32 and Store apps alike and gives each one a launch id.

Three things live here:

- :func:`catalogue` enumerates that folder (about a second, so it is cached and
  can be warmed up in the background).
- :func:`icon` resolves an app's icon, trying the package logo first for Store
  apps and the shell's own image pipeline for the rest.
- :func:`launch` starts an entry from its id, whatever kind it is.

Profiles store these targets as ``app:<launch id>``. The prefix is what tells an
id apart from a path or a URL, and it keeps old profiles working untouched.

Nothing here raises: without Windows, or with an unreadable shell, the catalogue
is simply empty and the target field behaves as it always did.
"""

from __future__ import annotations

import base64
import logging
import os
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET

log = logging.getLogger("hotkeyconfig.apps")

IS_WINDOWS = sys.platform == "win32"
PREFIX = "app:"          # marca de "esto es una app del catalogo", no una ruta

_lock = threading.Lock()
_catalogue: list[dict] | None = None
_icons: dict[str, str] = {}


# --- catalogue -----------------------------------------------------------

def _is_noise(app_id: str, name: str) -> bool:
    """Entries that are not really apps somebody would bind to a key.

    The AppsFolder also lists help files, uninstallers, web links and Control
    Panel applets. Real apps use their own launch id or a plain executable, so
    dropping these has no false positives worth worrying about, and anything
    hidden here can still be picked with the Browse button.
    """
    low = app_id.lower()
    if low.startswith(("http://", "https://")):
        return True
    if low.endswith((".url", ".msc", ".chm", ".txt", ".htm", ".html", ".pdf", ".rtf")):
        return True
    # Control Panel and system applets hide under a CLSID folder: "{GUID}\tool".
    if len(app_id) > 38 and app_id[0] == "{" and app_id.find("}") == 37:
        return True
    if low.startswith(("microsoft.windows.", "windows.immersivecontrolpanel")):
        return True
    if "\\windows kits\\" in low or "\\vulkansdk\\" in low:
        return True
    base = os.path.basename(low)
    if base.startswith(("unins", "uninstall", "setup.exe")):
        return True
    stem = name.lower()
    return stem.startswith(("desinstalar ", "uninstall ", "remove "))


def _our_shortcuts() -> set[str]:
    """Names of the shortcuts this program creates for "works with the app closed".

    They live in the Start menu, which is exactly what the AppsFolder lists, so
    without this the catalogue offers entries like "Capa 1 - T4" as if they were
    applications. Worse, each one reports the launch id of the app it points at,
    so a real app could be shadowed by our own shortcut to it.
    """
    try:
        from . import standalone
        return {path.stem for path in standalone.folder().glob("*.lnk")}
    except Exception:  # noqa: BLE001
        return set()


def _enumerate() -> list[dict]:
    """Read the shell's AppsFolder. Runs on its own thread with COM started."""
    import pythoncom
    import win32com.client

    ours = _our_shortcuts()
    pythoncom.CoInitialize()
    try:
        folder = win32com.client.Dispatch("Shell.Application").NameSpace("shell:AppsFolder")
        found: list[dict] = []
        for item in folder.Items():
            try:
                app_id, name = item.Path, item.Name
                if not app_id or not name or name in ours or _is_noise(app_id, name):
                    continue
                # The install folder is only readable while enumerating: asking for
                # it later, item by item, comes back empty. It is what gives Store
                # apps their icon, so it is picked up here even though most entries
                # do not have one.
                try:
                    package = item.ExtendedProperty("System.AppUserModel.PackageInstallPath") or ""
                except Exception:  # noqa: BLE001
                    package = ""
                found.append({"id": app_id, "name": name, "package": package})
            except Exception:  # noqa: BLE001 - one unreadable entry is not worth losing the rest
                continue
    finally:
        pythoncom.CoUninitialize()
    # Several entries can share a launch id (a desktop shortcut next to the app
    # itself). The one that knows its package wins, because that is the one whose
    # icon can be resolved.
    best: dict[str, dict] = {}
    for app in found:
        current = best.get(app["id"])
        if current is None or (app["package"] and not current["package"]):
            best[app["id"]] = app
    return sorted(best.values(), key=lambda a: a["name"].lower())


def catalogue(refresh: bool = False) -> list[dict]:
    """Installed apps as ``{"id", "name", "package"}``, cached after the first read."""
    global _catalogue
    if not IS_WINDOWS:
        return []
    with _lock:
        if _catalogue is not None and not refresh:
            return _catalogue
    try:
        found = _enumerate()
    except Exception:  # noqa: BLE001 - an empty catalogue only costs the suggestions
        log.exception("could not read the list of installed apps")
        found = []
    with _lock:
        _catalogue = found
    return found


def warm_up() -> None:
    """Read the catalogue in the background, so the first search is instant."""
    if not IS_WINDOWS:
        return
    threading.Thread(target=catalogue, daemon=True).start()


def find(app_id: str) -> dict | None:
    for app in catalogue():
        if app["id"] == app_id:
            return app
    return None


# --- icons ---------------------------------------------------------------

def _png_data_uri(raw: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def _package_logo(package: str, app_id: str, size: int) -> str:
    """Icon of a Store app, taken from the logo declared in its manifest.

    The shell renders a blank sheet of paper for some packaged apps (Spotify is
    one), so the file itself is used instead. Windows ships every logo in a range
    of sizes; the closest one at or above the requested size wins, and the
    "unplated" variant is preferred because it has no solid square behind it.
    """
    manifest = os.path.join(package, "AppxManifest.xml")
    if not os.path.isfile(manifest):
        return ""
    wanted_id = app_id.split("!", 1)[1] if "!" in app_id else ""
    logo = ""
    try:
        root = ET.parse(manifest).getroot()
        for app in root.iter():
            if not app.tag.endswith("}Application") and app.tag != "Application":
                continue
            if wanted_id and app.get("Id") != wanted_id:
                continue
            for visual in app.iter():
                logo = visual.get("Square44x44Logo") or visual.get("Logo") or logo
                if logo:
                    break
            if logo:
                break
    except Exception:  # noqa: BLE001
        return ""
    if not logo:
        return ""
    logo = logo.replace("/", os.sep)
    folder = os.path.join(package, os.path.dirname(logo))
    stem = os.path.splitext(os.path.basename(logo))[0]
    if not os.path.isdir(folder):
        return ""
    best, best_score = "", None
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return ""
    for entry in entries:
        name = entry.name
        if not name.lower().endswith(".png") or not name.startswith(stem):
            continue
        tag = name[len(stem):].lower()
        # High contrast variants are black-on-white or white-on-black shapes meant
        # for accessibility themes. One of them used to win and paint Spotify as a
        # white rectangle, which looked exactly like a missing icon.
        if "contrast-" in tag:
            continue
        if "targetsize-" in tag:
            try:
                px = int(tag.split("targetsize-", 1)[1].split("_", 1)[0].split(".", 1)[0])
            except ValueError:
                continue
        elif "scale-" in tag:
            try:
                px = 44 * int(tag.split("scale-", 1)[1].split("_", 1)[0].split(".", 1)[0]) // 100
            except ValueError:
                continue
        else:
            px = 44
        # Closest at or above the wanted size; below it, the biggest available.
        score = (0, px - size) if px >= size else (1, size - px)
        if "lightunplated" in tag:      # made for light themes, washed out on dark
            score = (score[0] + 2, score[1])
        elif "unplated" in tag:         # no solid backplate: what we want
            score = (score[0] - 1, score[1])
        if best_score is None or score < best_score:
            best, best_score = entry.path, score
    if not best:
        return ""
    try:
        with open(best, "rb") as fh:
            return _png_data_uri(fh.read())
    except OSError:
        return ""


def _shell_icon(app_id: str, size: int) -> str:
    """Icon through the shell's own image pipeline (IShellItemImageFactory).

    Same pipeline the Start menu uses, so it is right for every kind of entry,
    with no shortcut arrow on top and no need to resolve targets by hand.
    """
    import ctypes
    from ctypes import POINTER, byref, c_int, c_void_p, c_wchar_p
    from ctypes.wintypes import HBITMAP, INT

    class GUID(ctypes.Structure):
        _fields_ = [("d1", ctypes.c_uint32), ("d2", ctypes.c_uint16),
                    ("d3", ctypes.c_uint16), ("d4", ctypes.c_ubyte * 8)]

    class SIZE(ctypes.Structure):
        _fields_ = [("cx", c_int), ("cy", c_int)]

    class BITMAP(ctypes.Structure):
        _fields_ = [("bmType", ctypes.c_long), ("bmWidth", ctypes.c_long),
                    ("bmHeight", ctypes.c_long), ("bmWidthBytes", ctypes.c_long),
                    ("bmPlanes", ctypes.c_ushort), ("bmBitsPixel", ctypes.c_ushort),
                    ("bmBits", c_void_p)]

    ole32 = ctypes.WinDLL("ole32")
    shell32 = ctypes.WinDLL("shell32")
    gdi32 = ctypes.WinDLL("gdi32")

    iid = GUID()
    ole32.CLSIDFromString(c_wchar_p("{bcc18b79-ba16-442f-80c4-8a59c30c463b}"), byref(iid))
    ptr = c_void_p()
    if shell32.SHCreateItemFromParsingName(
            c_wchar_p("shell:AppsFolder\\" + app_id), None, byref(iid), byref(ptr)) != 0 or not ptr:
        return ""
    vtable = ctypes.cast(ptr, POINTER(POINTER(c_void_p))).contents
    get_image = ctypes.WINFUNCTYPE(ctypes.HRESULT, c_void_p, SIZE, INT, POINTER(HBITMAP))(vtable[3])
    release = ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)(vtable[2])
    hbitmap = HBITMAP()
    try:
        try:
            get_image(ptr, SIZE(size, size), 0x1, byref(hbitmap))   # SIIGBF_BIGGERSIZEOK
        except OSError:
            return ""
        if not hbitmap:
            return ""
        try:
            bitmap = BITMAP()
            if not gdi32.GetObjectW(hbitmap, ctypes.sizeof(BITMAP), byref(bitmap)):
                return ""
            # The shell hands back a top-down 32bpp premultiplied BGRA DIB.
            if not bitmap.bmBits or bitmap.bmBitsPixel != 32:
                return ""
            raw = ctypes.string_at(bitmap.bmBits, bitmap.bmWidthBytes * bitmap.bmHeight)
            return _bgra_to_png(raw, bitmap.bmWidth, bitmap.bmHeight)
        finally:
            gdi32.DeleteObject(hbitmap)
    finally:
        release(ptr)


def _target_exe(app_id: str) -> str:
    """The executable an entry really launches, when it is a plain one."""
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    try:
        folder = win32com.client.Dispatch("Shell.Application").NameSpace("shell:AppsFolder")
        item = folder.ParseName(app_id)
        if item is None:
            return ""
        target = item.ExtendedProperty("System.Link.TargetParsingPath") or ""
        return target if target.lower().endswith(".exe") and os.path.isfile(target) else ""
    except Exception:  # noqa: BLE001
        return ""
    finally:
        pythoncom.CoUninitialize()


def _exe_icon(path: str, size: int) -> str:
    """Icon out of an executable's own resources."""
    if not path:
        return ""
    import ctypes
    from ctypes import wintypes
    from io import BytesIO

    import win32gui
    import win32ui
    from PIL import Image

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    handles = (wintypes.HICON * 1)()
    if user32.PrivateExtractIconsW(path, 0, size, size, handles, None, 1, 0) <= 0 or not handles[0]:
        return ""
    try:
        screen = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(screen, size, size)
        memory = screen.CreateCompatibleDC()
        memory.SelectObject(bitmap)
        win32gui.DrawIconEx(memory.GetSafeHdc(), 0, 0, handles[0], size, size, 0, None, 0x0003)
        info = bitmap.GetInfo()
        image = Image.frombuffer("RGBA", (info["bmWidth"], info["bmHeight"]),
                                 bitmap.GetBitmapBits(True), "raw", "BGRA", 0, 1)
        out = BytesIO()
        image.save(out, "PNG")
        return _png_data_uri(out.getvalue())
    except Exception:  # noqa: BLE001
        return ""
    finally:
        user32.DestroyIcon(handles[0])


def _bgra_to_png(raw: bytes, width: int, height: int) -> str:
    from io import BytesIO

    from PIL import Image

    # Orientacion -1: el shell entrega el mapa de bits de abajo arriba, asi que
    # leerlo del derecho sacaba los iconos boca abajo. Cuesta verlo porque medio
    # catalogo son circulos (Chrome, Spotify, Steam), pero Discord, GIMP, Aseprite
    # o Inkscape salian del reves. Comparado contra el icono del propio .exe.
    image = Image.frombuffer("RGBA", (width, height), raw, "raw", "BGRA", 0, -1)
    if _looks_blank(image):
        return ""
    out = BytesIO()
    image.save(out, "PNG")
    return _png_data_uri(out.getvalue())


def _looks_blank(image) -> bool:
    """Is this the shell's blank-sheet placeholder rather than a real icon?

    That placeholder is a small grey glyph on a mostly empty canvas: it covers
    little and has no colour at all, while real icons either fill the canvas or
    are colourful. Saying so lets the caller try another source instead of
    showing a sheet of paper.
    """
    try:
        small = image.convert("RGBA").resize((32, 32))
        opaque = colourful = 0
        for r, g, b, a in small.getdata():
            if a <= 32:
                continue
            opaque += 1
            if max(r, g, b) - min(r, g, b) > 24:
                colourful += 1
        if not opaque:
            return True
        return opaque / 1024.0 < 0.22 and colourful / opaque < 0.03
    except Exception:  # noqa: BLE001
        return False


def icon(app_id: str, size: int = 32) -> str:
    """A ``data:`` PNG for an app, or an empty string when there is none."""
    if not IS_WINDOWS or not app_id:
        return ""
    key = f"{app_id}@{size}"
    with _lock:
        if key in _icons:
            return _icons[key]
    result = ""
    try:
        app = find(app_id)
        package = (app or {}).get("package") or ""
        if package:
            result = _package_logo(package, app_id, size)
        if not result:
            result = _shell_icon(app_id, size)
        if not result:
            # Last resort for launcher stubs (Discord's Update.exe and friends):
            # the icon baked into the executable the entry really points at.
            result = _exe_icon(_target_exe(app_id), size)
    except Exception:  # noqa: BLE001 - an app with no icon is not a failure
        log.debug("no icon for %s", app_id, exc_info=True)
        result = ""
    with _lock:
        _icons[key] = result
    return result


def icons(app_ids: list[str], size: int = 32) -> dict[str, str]:
    """Icons for several apps in one call (the interface asks per visible row)."""
    return {app_id: icon(app_id, size) for app_id in app_ids}


# --- launching -----------------------------------------------------------

def is_app_target(target: str) -> bool:
    return bool(target) and target.startswith(PREFIX)


def app_id_of(target: str) -> str:
    return target[len(PREFIX):] if is_app_target(target) else target


def launch(app_id: str) -> None:
    """Start a catalogue entry, Win32 or Store alike.

    Explorer is the one that knows how to activate every kind of entry, from a
    Store app id to a plain executable, so the shell is asked to do it rather
    than guessing here.
    """
    if not app_id:
        return
    if os.path.isabs(app_id) and os.path.exists(app_id):
        os.startfile(app_id)  # type: ignore[attr-defined]
        return
    subprocess.Popen(["explorer.exe", "shell:AppsFolder\\" + app_id])


def display_name(target: str) -> str:
    """What to show for a stored target: the app's name if it is one."""
    if not is_app_target(target):
        return target
    app = find(app_id_of(target))
    return app["name"] if app else app_id_of(target)
