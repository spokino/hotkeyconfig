"""Actions that work without the listener, handed over to Windows itself.

A macropad can only send keystrokes: opening a program or a link is an order
someone has to carry out on the computer, and normally that someone is our
listener. But Windows already offers a way to run something on a key combination:
a shortcut with a hotkey assigned, watched by Explorer, which is always running.

So for "open" actions the work can be handed to the system. The key keeps sending
its unique combo, a shortcut in the Start menu answers to that combo, and nothing
of ours needs to be running.

What this cannot do, no matter how it is written:

- Put the configuration inside the keyboard. It lives in Windows, in these
  shortcuts. Plugged into another computer the keyboard still only sends its
  combos, and there nothing will happen.
- Cover knobs. Their combos include the Windows key and Windows refuses it as a
  shortcut hotkey (measured, not assumed). Knobs already do volume and playback
  without software anyway, since those are real media keys.
- Cover anything other than opening things: typing text, running scripts or the
  colour flash all need a program to be listening.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path

log = logging.getLogger("hotkeyconfig.standalone")

IS_WINDOWS = sys.platform == "win32"

# Explorer only honours the hotkey of shortcuts living in the Start menu or on the
# desktop. The Start menu keeps the desktop clean.
#
# A subfolder of its own, NOT the program's own Start menu group: the installer
# puts the app shortcut in that group, and the cleanup below would delete it. That
# is not hypothetical, it happened during development and left the machine without
# a way to launch the app from the Start menu.
FOLDER_NAME = os.path.join("HotKeyConfig", "Keys")

# Written into every shortcut this module creates, and required before deleting
# one. Belt and braces: even pointed at the wrong folder, it cannot remove
# somebody else's shortcut.
_SIGNATURE = "HotKeyConfig key:"

# Modifiers Windows accepts on a shortcut hotkey. Measured on Windows 11: anything
# including the Windows key is rejected outright.
_ALLOWED_MODIFIERS = {"ctrl", "alt", "shift"}


def folder() -> Path:
    return (Path(os.environ.get("APPDATA", str(Path.home()))) /
            "Microsoft" / "Windows" / "Start Menu" / "Programs" / FOLDER_NAME)


def combo_supported(combo: str) -> bool:
    """Whether Windows would accept this combo as a shortcut hotkey."""
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    if len(parts) < 2:
        return False
    modifiers, key = parts[:-1], parts[-1]
    if not modifiers or any(m not in _ALLOWED_MODIFIERS for m in modifiers):
        return False
    return bool(re.fullmatch(r"f([1-9]|1[0-9]|2[0-4])|[a-z0-9]", key))


def to_hotkey(combo: str) -> str:
    """``ctrl+alt+f15`` -> ``Ctrl+Alt+F15``, the spelling the shortcut expects."""
    return "+".join(p.strip().capitalize() if not p.strip().lower().startswith("f")
                    or not p.strip()[1:].isdigit() else p.strip().upper()
                    for p in combo.split("+") if p.strip())


def _same_hotkey(one: str, other: str) -> bool:
    """Compare hotkeys ignoring the order of the modifiers.

    Windows stores them in its own order: write ``Ctrl+Alt+F15`` and it comes back
    as ``Alt+Ctrl+F15``. Comparing the strings as they are would report a
    difference every single time.
    """
    def normalise(value: str) -> str:
        return "+".join(sorted(p.strip().lower() for p in str(value).split("+") if p.strip()))
    return normalise(one) == normalise(other)


def _split_command(command: str) -> tuple[str, str]:
    """Split a registry command line into executable and the rest."""
    command = command.strip()
    if command.startswith('"'):
        exe, _, rest = command[1:].partition('"')
        return exe, rest.strip()
    exe, _, rest = command.partition(" ")
    return exe, rest.strip()


def _store_app(uri: str) -> str:
    """Target for a Microsoft Store app whose protocol is not in the registry.

    Store apps (Spotify, WhatsApp and so on) are not plain executables: their
    folder under WindowsApps carries the version number and changes on every
    update, and their protocol has no command in the registry. Windows does list
    them with an application id, and a shortcut pointing at ``shell:AppsFolder``
    launches them, hotkey included (measured).
    """
    if not IS_WINDOWS:
        return ""
    name = uri.split(":", 1)[0]
    if not name.isalnum():
        return ""
    try:
        import subprocess

        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "Get-StartApps | Where-Object { $_.Name -like '*" + name + "*' } "
             "| Select-Object -First 1 -ExpandProperty AppID"],
            capture_output=True, text=True, timeout=20, creationflags=0x08000000)
    except Exception:  # noqa: BLE001
        log.debug("could not ask Windows for the app id of %s", name, exc_info=True)
        return ""
    app_id = out.stdout.strip()
    return rf"shell:AppsFolder\{app_id}" if app_id else ""


def _protocol_command(uri: str) -> tuple[str, str]:
    """Program registered for a scheme like ``spotify:``, and its arguments."""
    if not IS_WINDOWS:
        return "", ""
    import winreg

    scheme = uri.split(":", 1)[0]
    if not scheme.isalnum():
        return "", ""
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"{scheme}\shell\open\command") as key:
            command = str(winreg.QueryValueEx(key, "")[0])
    except OSError:
        return "", ""
    exe, rest = _split_command(os.path.expandvars(command))
    if not os.path.isfile(exe):
        return "", ""
    return exe, (rest.replace("%1", uri) if "%1" in rest else uri)


def _target_and_args(action_params: dict) -> tuple[str, str]:
    """Executable and arguments for an ``open`` action.

    The real program has to be the target. Pointing the shortcut at Explorer and
    letting it forward the address does work when double clicked, but Windows
    ignores it when it comes from the hotkey (measured, not assumed), and the key
    silently does nothing.
    """
    target = str(action_params.get("target", "")).strip()
    if not target:
        return "", ""

    # An app picked from the installed list already carries the id Windows uses to
    # launch it, so there is nothing to guess: no registry lookup and no asking
    # PowerShell for it, which is what the older "spotify:" path had to do.
    from . import apps
    if apps.is_app_target(target):
        app_id = apps.app_id_of(target)
        if os.path.isabs(app_id) and os.path.exists(app_id):
            return app_id, ""
        return rf"shell:AppsFolder\{app_id}", ""

    if target.startswith(("http://", "https://")):
        from . import browsers
        exe = browsers.resolve(action_params.get("browser")) or browsers.default_browser()
        return (exe, target) if exe else ("", "")

    expanded = os.path.expandvars(target)
    if os.path.exists(expanded):
        return expanded, ""
    if ":" in target and not os.path.isabs(target):   # spotify:, mailto:, obsidian:...
        exe, arguments = _protocol_command(target)
        if exe:
            return exe, arguments
        return _store_app(target), ""
    return "", ""


def _safe_name(label: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", label).strip() or "action"


def write(label: str, combo: str, action_params: dict) -> tuple[Path, bool] | None:
    """Create the shortcut that makes one key work without the listener.

    Returns ``(path, rewritten)``, or None when this action cannot be handed over
    to Windows. ``rewritten`` is False when the shortcut was already correct.
    """
    if not IS_WINDOWS or not combo_supported(combo):
        return None
    target, arguments = _target_and_args(action_params)
    if not target:
        return None

    import win32com.client   # lazy: only needed when a key uses this

    path = folder() / f"{_safe_name(label)}.lnk"
    path.parent.mkdir(parents=True, exist_ok=True)
    shell = win32com.client.Dispatch("WScript.Shell")
    hotkey = to_hotkey(combo)

    # An unchanged shortcut is left exactly as it is. Explorer keeps a table of
    # these hotkeys, and deleting or rewriting one can leave the old entry behind:
    # the combo then answers to a shortcut that no longer exists and the key stops
    # working until Explorer restarts. Rewriting for nothing is not free.
    if path.exists():
        try:
            current = shell.CreateShortCut(str(path))
            same_target = (current.TargetPath == target or
                           (not current.TargetPath and target.startswith("shell:")))
            if (same_target and current.Arguments == arguments
                    and _same_hotkey(current.Hotkey, hotkey)):
                log.debug("shortcut for %s already up to date", label)
                return path, False
        except Exception:  # noqa: BLE001 - unreadable, rewrite it
            log.debug("could not read %s", path, exc_info=True)

    link = shell.CreateShortCut(str(path))
    link.TargetPath = target
    link.Arguments = arguments
    link.Hotkey = hotkey
    link.Description = f"{_SIGNATURE} {label}"
    link.Save()
    log.info("shortcut written for %s (%s)", label, combo)
    return path, True


def _is_ours(path: Path) -> bool:
    """Whether this shortcut was created by this module. Checked before deleting."""
    try:
        import win32com.client

        shell = win32com.client.Dispatch("WScript.Shell")
        return str(shell.CreateShortCut(str(path)).Description).startswith(_SIGNATURE)
    except Exception:  # noqa: BLE001 - unreadable means not ours, so leave it alone
        log.debug("could not read %s", path, exc_info=True)
        return False


def _delete(path: Path) -> bool:
    if not _is_ours(path):
        log.debug("left alone, not ours: %s", path)
        return False
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        log.debug("could not remove %s", path, exc_info=True)
        return False


def remove(label: str) -> None:
    _delete(folder() / f"{_safe_name(label)}.lnk")


def label_for(layer_name: str, index: int) -> str:
    """Stable name for one key's shortcut, readable in the Start menu."""
    return f"{layer_name} - T{index + 1}"


def sync(profile) -> dict:
    """Bring the shortcut folder in line with the profile.

    Called when saving: keys marked as standalone get their shortcut, and the ones
    that no longer are lose it. Leftovers would keep firing after the action has
    changed, which is worse than not working at all.
    """
    result = {"written": 0, "unchanged": 0, "removed": 0, "skipped": []}
    if not IS_WINDOWS:
        return result

    wanted: dict[str, tuple[str, dict]] = {}
    for layer in profile.layers:
        for index, binding in enumerate(layer.buttons):
            if not getattr(binding, "standalone", False):
                continue
            if binding.action.type != "open":
                continue
            label = label_for(layer.name, index)
            if not combo_supported(binding.combo):
                result["skipped"].append(label)
                continue
            wanted[label] = (binding.combo, binding.action.params)

    directory = folder()
    if directory.is_dir():
        keep = {_safe_name(k) for k in wanted}
        for path in directory.glob("*.lnk"):
            if path.stem not in keep and _delete(path):
                result["removed"] += 1

    for label, (combo, params) in wanted.items():
        try:
            done = write(label, combo, params)
            if done is None:
                # Nothing to point the shortcut at: some things simply cannot be
                # opened without a program running, and saying so beats leaving a
                # shortcut that does nothing.
                result["skipped"].append(label)
            elif done[1]:
                result["written"] += 1
            else:
                result["unchanged"] += 1
        except Exception:  # noqa: BLE001 - one bad shortcut must not block saving
            log.exception("could not write the shortcut for %s", label)
            result["skipped"].append(label)
    return result


def clear() -> int:
    """Remove every shortcut this program created. Returns how many."""
    directory = folder()
    if not directory.is_dir():
        return 0
    return sum(1 for path in directory.glob("*.lnk") if _delete(path))
