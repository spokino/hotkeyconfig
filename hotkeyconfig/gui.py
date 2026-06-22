"""Configurador gráfico (tkinter, sin dependencias extra).

Muestra las 12 teclas y las 2 perillas por capa; al hacer clic en un control se
elige su acción. Desde aquí se guarda el perfil, se graba en el teclado (HID) y
se arranca/para el listener de fondo.
"""

from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from . import combos
from .profile import Action, Profile, load, save

ACTION_TYPES = [
    "unassigned", "run", "open", "text", "media", "native", "hotkey", "window", "sequence",
]
MEDIA_KEYS = ["volume_up", "volume_down", "mute", "play_pause", "next", "previous", "stop"]
WINDOW_OPS = ["minimize", "maximize", "restore", "close"]

# Descripción humana de cada tipo (para la ayuda inline).
TYPE_HELP = {
    "unassigned": "Sin asignar (no hace nada).",
    "run": "Ejecuta un script o comando.",
    "open": "Abre una app, carpeta o URL.",
    "text": "Escribe/pega un texto.",
    "media": "Tecla multimedia (vía la app de fondo).",
    "native": "Tecla multimedia grabada en el teclado (no necesita la app).",
    "hotkey": "Envía un atajo a la app activa (ej: ctrl+c).",
    "window": "Minimiza/maximiza/cierra la ventana activa.",
    "sequence": "Varias acciones en orden (se edita en profile.yaml).",
}


def action_summary(action: Action) -> str:
    t, p = action.type, action.params
    if t == "unassigned":
        return "—"
    if t == "run":
        return "run: " + (p.get("cmd") or " ".join(p.get("args", [])))[:26]
    if t == "open":
        return "open: " + str(p.get("target", ""))[:26]
    if t == "text":
        return "text: " + str(p.get("text", ""))[:22]
    if t in ("media", "native"):
        return f"{t}: {p.get('key', '')}"
    if t == "hotkey":
        return "hotkey: " + str(p.get("send", ""))
    if t == "window":
        return "window: " + str(p.get("do", ""))
    if t == "sequence":
        return f"sequence ({len(p.get('steps', []))})"
    return t


class ActionEditor(tk.Toplevel):
    """Diálogo modal para editar la acción de un control."""

    def __init__(self, master, label: str, action: Action, on_save):
        super().__init__(master)
        self.title(f"Acción · {label}")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.action = action
        self.on_save = on_save
        self.entries: dict[str, tk.Variable] = {}

        ttk.Label(self, text=label, font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 4), sticky="w")

        ttk.Label(self, text="Tipo de acción:").grid(row=1, column=0, padx=12, sticky="w")
        self.type_var = tk.StringVar(value=action.type)
        combo = ttk.Combobox(self, values=ACTION_TYPES, textvariable=self.type_var,
                             state="readonly", width=18)
        combo.grid(row=1, column=1, padx=12, pady=4, sticky="w")
        combo.bind("<<ComboboxSelected>>", lambda e: self._rebuild())

        self.help = ttk.Label(self, text="", foreground="#666", wraplength=320)
        self.help.grid(row=2, column=0, columnspan=2, padx=12, sticky="w")

        self.fields = ttk.Frame(self)
        self.fields.grid(row=3, column=0, columnspan=2, padx=12, pady=6, sticky="we")

        btns = ttk.Frame(self)
        btns.grid(row=4, column=0, columnspan=2, pady=(6, 12))
        ttk.Button(btns, text="Guardar", command=self._save).pack(side="left", padx=6)
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side="left", padx=6)

        self._rebuild()

    def _add_field(self, key: str, label: str, default: str = "", values=None):
        row = len(self.entries)
        ttk.Label(self.fields, text=label).grid(row=row, column=0, sticky="w", pady=3)
        var = tk.StringVar(value=str(default))
        if values:
            w = ttk.Combobox(self.fields, values=values, textvariable=var, state="readonly", width=30)
        else:
            w = ttk.Entry(self.fields, textvariable=var, width=33)
        w.grid(row=row, column=1, sticky="we", pady=3, padx=(6, 0))
        self.entries[key] = var

    def _rebuild(self):
        for child in self.fields.winfo_children():
            child.destroy()
        self.entries.clear()
        t = self.type_var.get()
        self.help.config(text=TYPE_HELP.get(t, ""))
        p = self.action.params if self.action.type == t else {}
        if t == "run":
            self._add_field("cmd", "Comando", p.get("cmd", ""))
            self._add_field("cwd", "Carpeta (opcional)", p.get("cwd", ""))
        elif t == "open":
            self._add_field("target", "App / carpeta / URL", p.get("target", ""))
        elif t == "text":
            self._add_field("text", "Texto", p.get("text", ""))
        elif t in ("media", "native"):
            self._add_field("key", "Tecla", p.get("key", "volume_up"), values=MEDIA_KEYS)
        elif t == "hotkey":
            self._add_field("send", "Atajo (ej: ctrl+c)", p.get("send", ""))
        elif t == "window":
            self._add_field("do", "Operación", p.get("do", "minimize"), values=WINDOW_OPS)
        elif t == "sequence":
            ttk.Label(self.fields, text="Edítalo en profile.yaml por ahora.",
                      foreground="#999").grid(row=0, column=0, columnspan=2, sticky="w")

    def _save(self):
        t = self.type_var.get()
        params = {k: v.get() for k, v in self.entries.items() if v.get() != ""}
        self.action.type = t
        self.action.params = params if t != "sequence" else self.action.params
        self.on_save()
        self.destroy()


class App(tk.Tk):
    def __init__(self, profile_path: Path):
        super().__init__()
        self.title("hotkeyconfig — configurador")
        self.geometry("720x560")
        self.profile_path = profile_path
        self.profile: Profile = self._load_or_create()
        self.listener: subprocess.Popen | None = None
        self.dirty = False

        self._build_toolbar()
        self._build_layer_selector()
        self.grid_frame = ttk.Frame(self, padding=10)
        self.grid_frame.pack(fill="both", expand=True)
        self.status = ttk.Label(self, text="", anchor="w", relief="sunken")
        self.status.pack(fill="x", side="bottom")

        self._render_layer()
        self._refresh_device(loop=True)

    # --- carga ----------------------------------------------------------
    def _load_or_create(self) -> Profile:
        if self.profile_path.exists():
            return load(self.profile_path)
        from .cli import build_default_profile
        prof = build_default_profile()
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        save(prof, self.profile_path)
        return prof

    # --- UI -------------------------------------------------------------
    def _build_toolbar(self):
        bar = ttk.Frame(self, padding=(10, 8))
        bar.pack(fill="x")
        self.dev_label = ttk.Label(bar, text="Teclado: …", font=("Segoe UI", 9, "bold"))
        self.dev_label.pack(side="left")
        ttk.Button(bar, text="💾 Guardar", command=self._save).pack(side="right", padx=3)
        ttk.Button(bar, text="⚡ Flashear teclado", command=self._flash).pack(side="right", padx=3)
        self.listen_btn = ttk.Button(bar, text="▶ Iniciar listener", command=self._toggle_listener)
        self.listen_btn.pack(side="right", padx=3)

    def _build_layer_selector(self):
        sel = ttk.Frame(self, padding=(10, 0))
        sel.pack(fill="x")
        ttk.Label(sel, text="Capa:").pack(side="left")
        self.layer_var = tk.IntVar(value=0)
        for i in range(combos.LAYERS):
            ttk.Radiobutton(sel, text=f"Capa {i + 1}", variable=self.layer_var,
                            value=i, command=self._render_layer).pack(side="left", padx=4)
        ttk.Label(sel, text="  (la capa se cambia con el botón lateral del teclado)",
                  foreground="#888").pack(side="left")

    def _render_layer(self):
        for child in self.grid_frame.winfo_children():
            child.destroy()
        layer = self.profile.layers[self.layer_var.get()]

        keys = ttk.LabelFrame(self.grid_frame, text="Teclas", padding=8)
        keys.pack(side="left", fill="both", expand=True)
        for idx, binding in enumerate(layer.buttons):
            r, c = divmod(idx, self.profile.device.columns)
            b = tk.Button(keys, width=14, height=3, justify="center",
                          text=f"T{idx + 1}\n{action_summary(binding.action)}",
                          command=lambda b=binding, n=idx + 1: self._edit(f"Tecla {n}", b))
            b.grid(row=r, column=c, padx=4, pady=4)

        knobs = ttk.LabelFrame(self.grid_frame, text="Perillas", padding=8)
        knobs.pack(side="left", fill="y", padx=(10, 0))
        for ki, knob in enumerate(layer.knobs):
            kf = ttk.LabelFrame(knobs, text=f"Perilla {ki + 1}", padding=6)
            kf.pack(fill="x", pady=4)
            for act, txt in (("ccw", "◀ Girar izq."), ("press", "● Pulsar"), ("cw", "Girar der. ▶")):
                binding = knob[act]
                tk.Button(kf, width=18, anchor="w",
                          text=f"{txt}: {action_summary(binding.action)}",
                          command=lambda b=binding, n=ki + 1, a=txt:
                          self._edit(f"Perilla {n} · {a}", b)).pack(fill="x", pady=2)

    def _edit(self, label: str, binding):
        ActionEditor(self, label, binding.action, on_save=self._after_edit)

    def _after_edit(self):
        self.dirty = True
        self._render_layer()
        self._set_status("Cambios sin guardar. Pulsa 💾 Guardar.")

    # --- acciones -------------------------------------------------------
    def _save(self):
        try:
            self.profile.validate()
            save(self.profile, self.profile_path)
            self.dirty = False
            self._set_status(f"Guardado en {self.profile_path}")
            if self.listener and self.listener.poll() is None and messagebox.askyesno(
                "Recargar", "El listener está activo. ¿Reiniciarlo para aplicar los cambios?"):
                self._stop_listener()
                self._start_listener()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error al guardar", str(exc))

    def _flash(self):
        from . import hid_flasher
        if not hid_flasher.is_connected():
            messagebox.showwarning("Sin teclado", "No veo el teclado conectado.")
            return
        if self.dirty:
            self._save()
        if not messagebox.askyesno(
            "Flashear", "Se grabarán los combos en la MEMORIA del teclado. ¿Continuar?"):
            return
        try:
            n = hid_flasher.flash(self.profile)
            self._set_status(f"Flasheados {n} mensajes al teclado.")
            messagebox.showinfo("Listo", f"Teclado grabado ({n} mensajes).")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error al flashear", str(exc))

    def _toggle_listener(self):
        if self.listener and self.listener.poll() is None:
            self._stop_listener()
        else:
            self._start_listener()

    def _start_listener(self):
        pyw = Path(sys.executable).with_name("pythonw.exe")
        exe = str(pyw if pyw.exists() else sys.executable)
        self.listener = subprocess.Popen(
            [exe, "-m", "hotkeyconfig", "run", "--no-tray", "-p", str(self.profile_path)])
        self.listen_btn.config(text="■ Parar listener")
        self._set_status("Listener activo: las acciones ya responden.")

    def _stop_listener(self):
        if self.listener:
            self.listener.terminate()
            self.listener = None
        self.listen_btn.config(text="▶ Iniciar listener")
        self._set_status("Listener detenido.")

    def _refresh_device(self, loop: bool = False):
        try:
            from . import hid_flasher
            ok = hid_flasher.is_connected()
        except Exception:  # noqa: BLE001
            ok = False
        self.dev_label.config(
            text="Teclado: ✓ conectado" if ok else "Teclado: ✗ no detectado",
            foreground="#178a3a" if ok else "#b00020")
        if loop:
            self.after(3000, lambda: self._refresh_device(loop=True))

    def _set_status(self, text: str):
        self.status.config(text=text)


def run(profile_path: str | Path) -> int:
    App(Path(profile_path)).mainloop()
    return 0
