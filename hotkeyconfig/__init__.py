"""hotkeyconfig: program ch57x macropads and bind scripts and shortcuts to every key.

Open source app made of two halves: a flasher that writes unique combos into the
keyboard's own memory over native HID (the ch57x-keyboard-tool binary stays as an
optional alternative backend), and a local listener that watches for those combos
and runs actions (scripts, apps, text, media, windows and so on).
"""

__version__ = "0.4.0"
