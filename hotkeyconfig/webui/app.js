"use strict";

const MEDIA_KEYS = ["volume_up", "volume_down", "mute", "play_pause", "next", "previous", "stop"];
const WINDOW_OPS = ["minimize", "maximize", "restore", "close"];
const ORDER = ["unassigned", "run", "open", "text", "media", "native", "hotkey", "window", "sequence"];
const LED_MODE_KEYS = ["keep", "off", "backlight", "press", "shock", "shock2"];
const LED_COLOR_KEYS = ["white", "red", "orange", "yellow", "green", "cyan", "blue", "purple"];
const ORIENT_KEYS = ["normal", "upsidedown", "clockwise", "counterclockwise"];
const SIDE_KEYS = ["top", "right", "bottom", "left"];   // donde estan las perillas
const LED_HEX = { white: "#eeeeee", red: "#e24b4a", orange: "#ef9f27", yellow: "#f2d024", green: "#63c132", cyan: "#22c1c1", blue: "#3b82f6", purple: "#8b5cf6" };
const TYPE_COLOR = { unassigned: "var(--muted)", run: "var(--c-run)", open: "var(--c-open)", text: "var(--c-text)", media: "var(--c-media)", native: "var(--c-native)", hotkey: "var(--c-hotkey)", window: "var(--c-window)", sequence: "var(--c-sequence)" };
let BROWSERS = [];   // los que hay instalados, los da el sistema al arrancar
let MODELS = [];     // catalogo de teclados, lo da el backend al arrancar
const CUSTOM_ID = "custom";
const TYPE_FIELDS = {
  run: [{ k: "cmd", ph: "py C:/scripts/deploy.py" }, { k: "cwd", ph: "" }],
  open: [{ k: "target", ph: "https://github.com/Mun1to" },
         { k: "browser", list: () => [{ v: "", l: tr("browser_default") }].concat(BROWSERS.map((b) => ({ v: b.name, l: b.name }))) }],
  text: [{ k: "text", ph: "" }],
  media: [{ k: "key", opts: MEDIA_KEYS }], native: [{ k: "key", opts: MEDIA_KEYS }],
  hotkey: [{ k: "send", ph: "ctrl+shift+s" }],
  window: [{ k: "do", opts: WINDOW_OPS }],
};
const ICONS = {
  unassigned: '<path d="M12 5v14M5 12h14"/>', run: '<path d="M4 6l5 6-5 6"/><path d="M12 18h8"/>',
  open: '<path d="M14 4h6v6"/><path d="M20 4L10 14"/><path d="M18 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h6"/>',
  text: '<path d="M4 6h16M4 12h10M4 18h7"/>', media: '<path d="M11 5L6 9H3v6h3l5 4z"/><path d="M16 9a4 4 0 0 1 0 6"/>',
  native: '<path d="M11 5L6 9H3v6h3l5 4z"/><path d="M16 9a4 4 0 0 1 0 6"/>',
  hotkey: '<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/>',
  window: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/>',
  sequence: '<path d="M9 6h12M9 12h12M9 18h12M4 6h.01M4 12h.01M4 18h.01"/>',
};

const T = {
  es: {
    type_unassigned: "Sin asignar", type_run: "Ejecutar script / comando", type_open: "Abrir app / carpeta / URL",
    type_text: "Escribir texto", type_media: "Multimedia (Spotify, etc.)", type_native: "Multimedia nativo (en el teclado)",
    type_hotkey: "Enviar atajo", type_window: "Ventana activa", type_sequence: "Secuencia",
    hint_unassigned: "No hace nada.", hint_run: "Lanza un .py / .ps1 / .bat / programa.",
    hint_open: "Abre un programa, carpeta o web. Ej: spotify: o https://…", hint_text: "Escribe el texto al activar.",
    hint_media: "Tecla multimedia gestionada por el listener.", hint_native: "Se graba en el teclado; funciona sin la app. Requiere reflashear.",
    hint_hotkey: "Manda un atajo a la app activa, p. ej. ctrl+c.", hint_window: "Minimiza / maximiza / restaura / cierra.",
    hint_sequence: "Varias acciones en orden (se edita en profile.yaml).",
    fld_cmd: "Comando", fld_cwd: "Carpeta (opcional)", fld_target: "Destino", fld_text: "Texto", fld_key: "Tecla", fld_send: "Atajo", fld_do: "Operación",
    fld_browser: "Navegador (solo para enlaces)", browser_default: "El del sistema",
    u_keys: "teclas", u_and: "y", u_knob: "perilla", u_knobs: "perillas",
    model_custom: "Otro (a medida)", model_pending: "todavía no compatible",
    note_single_modifier: "En este modelo, de una secuencia de teclas solo se guardan los modificadores de la primera.",
    led_keep: "No tocar", led_off: "Apagada", led_backlight: "Fija", led_press: "Al pulsar", led_shock: "Onda", led_shock2: "Onda 2",
    white: "Blanco", red: "Rojo", orange: "Naranja", yellow: "Amarillo", green: "Verde", cyan: "Cian", blue: "Azul", purple: "Morado",
    or_normal: "Normal", or_upsidedown: "Del revés", or_clockwise: "90° horario", or_counterclockwise: "90° antihorario",
    side_top: "Arriba", side_right: "A la derecha", side_bottom: "Abajo", side_left: "A la izquierda",
    knob_ccw: "◀ Izquierda", knob_press: "● Pulsar", knob_cw: "▶ Derecha", key_word: "Tecla", knob_word: "Perilla", action_word: "Acción",
    connected: "teclado conectado", disconnected: "teclado no detectado", dev_unsupported: "teclado aún no compatible", listen_start: "Iniciar listener", listen_stop: "Parar listener",
    saved: "Guardado", executed: "Ejecutado", flashing: "Flasheando…", flashed: "Teclado grabado", listener_on: "Listener activo", listener_off: "Listener detenido", layout_applied: "Estructura aplicada",
    version_available: "Versión {v} disponible", update_now: "Actualizar", download: "Descargar", updating: "Descargando actualización…",
    confirm_flash: "Se grabarán los combos y la iluminación en la MEMORIA del teclado. ¿Continuar?",
    confirm_layout: "Cambiar la estructura regenera los combos (habrá que reflashear), pero conserva tus acciones. ¿Continuar?",
    cap_shortcut: "Pulsa el atajo del teclado", cap_from: "Pulsa la tecla ORIGEN", cap_to: "Pulsa la tecla DESTINO", cap_waiting: "Esperando…",
    none_hotkeys: "Ningún atajo todavía.", none_remaps: "Ningún remapeo todavía.", edit: "Editar", err: "Error",
    no_color: "Sin color",
    steps: [
      { t: "Conecta y flashea", b: "Enchufa el macropad y pulsa <b>Flashear teclado</b>. Se graban en su memoria los códigos únicos de cada tecla (persisten sin la app)." },
      { t: "Asigna acciones", b: "En <b>Macropad</b>, haz clic en una tecla o perilla y elige qué hace: abrir Spotify, ejecutar un script, escribir texto, multimedia… Usa <b>Probar</b> para verla en acción." },
      { t: "Atajos del teclado normal", b: "En <b>Atajos de teclado</b> graba cualquier combo (ej. Ctrl+Alt+S) y asígnale una acción, o remapea una tecla por otra." },
      { t: "Enciende el listener", b: "Pulsa <b>Iniciar listener</b> para que las acciones respondan. Se puede iniciar solo con Windows para no abrirlo cada vez." },
      { t: "Ajusta a tu hardware", b: "En <b>Macropad</b> cambia filas, columnas, perillas u orientación con los pasos de <b>Estructura</b>. La luz RGB se elige arriba, por capa." },
    ],
  },
  en: {
    type_unassigned: "Unassigned", type_run: "Run script / command", type_open: "Open app / folder / URL",
    type_text: "Type text", type_media: "Media (Spotify, etc.)", type_native: "Native media (on the keyboard)",
    type_hotkey: "Send shortcut", type_window: "Active window", type_sequence: "Sequence",
    hint_unassigned: "Does nothing.", hint_run: "Runs a .py / .ps1 / .bat / program.",
    hint_open: "Opens a program, folder or website. E.g. spotify: or https://…", hint_text: "Types the text when triggered.",
    hint_media: "Media key handled by the listener.", hint_native: "Stored on the keyboard; works without the app. Needs reflashing.",
    hint_hotkey: "Sends a shortcut to the active app, e.g. ctrl+c.", hint_window: "Minimize / maximize / restore / close.",
    hint_sequence: "Several actions in order (edit in profile.yaml).",
    fld_cmd: "Command", fld_cwd: "Folder (optional)", fld_target: "Target", fld_text: "Text", fld_key: "Key", fld_send: "Shortcut", fld_do: "Operation",
    fld_browser: "Browser (links only)", browser_default: "System default",
    u_keys: "keys", u_and: "and", u_knob: "knob", u_knobs: "knobs",
    model_custom: "Other (custom)", model_pending: "not supported yet",
    note_single_modifier: "On this model, only the modifiers of the first key in a sequence are stored.",
    led_keep: "Leave as is", led_off: "Off", led_backlight: "Solid", led_press: "On press", led_shock: "Wave", led_shock2: "Wave 2",
    white: "White", red: "Red", orange: "Orange", yellow: "Yellow", green: "Green", cyan: "Cyan", blue: "Blue", purple: "Purple",
    or_normal: "Normal", or_upsidedown: "Upside down", or_clockwise: "90° clockwise", or_counterclockwise: "90° counter-clockwise",
    side_top: "On top", side_right: "On the right", side_bottom: "Below", side_left: "On the left",
    knob_ccw: "◀ Left", knob_press: "● Press", knob_cw: "▶ Right", key_word: "Key", knob_word: "Knob", action_word: "Action",
    connected: "keyboard connected", disconnected: "keyboard not found", dev_unsupported: "keyboard not supported yet", listen_start: "Start listener", listen_stop: "Stop listener",
    saved: "Saved", executed: "Done", flashing: "Flashing…", flashed: "Keyboard written", listener_on: "Listener running", listener_off: "Listener stopped", layout_applied: "Structure applied",
    version_available: "Version {v} available", update_now: "Update", download: "Download", updating: "Downloading update…",
    confirm_flash: "This writes the combos and lighting into the keyboard's MEMORY. Continue?",
    confirm_layout: "Changing the structure regenerates the combos (you'll need to reflash), but keeps your actions. Continue?",
    cap_shortcut: "Press the keyboard shortcut", cap_from: "Press the SOURCE key", cap_to: "Press the TARGET key", cap_waiting: "Waiting…",
    none_hotkeys: "No shortcuts yet.", none_remaps: "No remaps yet.", edit: "Edit", err: "Error",
    no_color: "No colour",
    steps: [
      { t: "Connect and flash", b: "Plug in the macropad and press <b>Flash keyboard</b>. It writes each key's unique code into its memory (they persist without the app)." },
      { t: "Assign actions", b: "In <b>Macropad</b>, click a key or knob and pick what it does: open Spotify, run a script, type text, media… Use <b>Test</b> to see it in action." },
      { t: "Normal keyboard shortcuts", b: "In <b>Keyboard shortcuts</b> record any combo (e.g. Ctrl+Alt+S) and assign an action, or remap one key to another." },
      { t: "Turn on the listener", b: "Press <b>Start listener</b> so the actions respond. It can start with Windows so you don't open it every time." },
      { t: "Match your hardware", b: "In <b>Macropad</b> change rows, columns, knobs or orientation with the <b>Structure</b> steppers. RGB light is chosen at the top, per layer." },
    ],
  },
};
let LANG = "es";
const tr = (k) => (T[LANG] && T[LANG][k] != null ? T[LANG][k] : (T.es[k] != null ? T.es[k] : k));

const state = { profile: null, layer: 0, section: "pad", listener: false, dirty: false, update: null };
const $ = (id) => document.getElementById(id);
const api = () => window.pywebview.api;
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const svg = (t) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[t] || ICONS.unassigned}</svg>`;
function markDirty() { state.dirty = true; }

// --- desplegables propios (reemplazan al <select> nativo del SO) ----------
// El combo nativo de Windows rompe el tema oscuro en WebView2. Envolvemos cada
// <select> con un boton + menu propios, manteniendo el <select> real por debajo
// para no tocar la logica (lee .value, reasigna opciones y engancha onchange).
const CSELECTS = [];
let cselGlobalWired = false;
function closeAllMenus(except) { CSELECTS.forEach((e) => { if (e !== except && e.open) e.close(); }); }
function enhanceSelect(sel) {
  if (sel._enh) return sel._enh;
  const inline = !!sel.closest("header, .subbar, .layoutbar");
  const wrap = document.createElement("div");
  wrap.className = "csel" + (inline ? " inline" : "");
  sel.parentNode.insertBefore(wrap, sel);
  wrap.appendChild(sel);
  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.className = "csel-trigger";
  trigger.innerHTML = '<span class="csel-dot" style="display:none"></span><span class="csel-label"></span><svg class="csel-caret" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>';
  const menu = document.createElement("div");
  menu.className = "csel-menu";
  wrap.appendChild(trigger);
  wrap.appendChild(menu);          // fixed: no lo recorta el overflow del modal
  const dotEl = trigger.querySelector(".csel-dot");
  const labelEl = trigger.querySelector(".csel-label");
  const enh = { sel, wrap, trigger, menu, open: false, close, sync: syncLabel };
  sel._enh = enh;

  function syncLabel() {
    const o = sel.options[sel.selectedIndex];
    labelEl.textContent = o ? o.textContent : "";
    const col = o && o.dataset.color;
    if (col) { dotEl.style.display = ""; dotEl.style.background = col; } else dotEl.style.display = "none";
  }
  function buildMenu() {
    menu.innerHTML = "";
    Array.from(sel.options).forEach((o, i) => {
      const it = document.createElement("div");
      it.className = "csel-opt" + (i === sel.selectedIndex ? " sel" : "");
      const col = o.dataset.color;
      it.innerHTML = (col ? `<span class="csel-dot" style="background:${esc(col)}"></span>` : "") + '<span class="csel-optlbl"></span>';
      it.querySelector(".csel-optlbl").textContent = o.textContent;
      it.onclick = () => {
        sel.selectedIndex = i; syncLabel(); close();
        sel.dispatchEvent(new Event("input", { bubbles: true }));
        sel.dispatchEvent(new Event("change", { bubbles: true }));
      };
      menu.appendChild(it);
    });
  }
  function place() {
    const r = trigger.getBoundingClientRect();
    menu.style.minWidth = r.width + "px";
    // Centrado bajo el boton, sin salirse de la ventana.
    const left = r.left + r.width / 2 - menu.offsetWidth / 2;
    menu.style.left = Math.max(8, Math.min(left, window.innerWidth - menu.offsetWidth - 8)) + "px";
    let top = r.bottom + 5;
    if (top + menu.offsetHeight > window.innerHeight - 8) {
      const above = r.top - 5 - menu.offsetHeight;
      top = above > 8 ? above : Math.max(8, window.innerHeight - menu.offsetHeight - 8);
    }
    menu.style.top = top + "px";
  }
  function open() { closeAllMenus(enh); buildMenu(); menu.classList.add("show"); wrap.classList.add("open"); enh.open = true; place(); }
  function close() { menu.classList.remove("show"); wrap.classList.remove("open"); enh.open = false; }
  trigger.onclick = (e) => { e.preventDefault(); e.stopPropagation(); enh.open ? close() : open(); };

  new MutationObserver(() => { syncLabel(); if (enh.open) { buildMenu(); place(); } }).observe(sel, { childList: true, subtree: true });
  syncLabel();
  CSELECTS.push(enh);
  if (!cselGlobalWired) {
    cselGlobalWired = true;
    document.addEventListener("click", () => closeAllMenus());
    window.addEventListener("keydown", (e) => { if (e.key === "Escape") closeAllMenus(); });
    // Al hacer scroll en la pagina el menu (position:fixed) quedaria descolgado de
    // su boton, asi que se cierra. Pero un menu con muchas opciones tiene su propia
    // barra de scroll: usarla NO debe cerrarlo.
    window.addEventListener("scroll", (e) => {
      const t = e.target;
      if (t && t.closest && t.closest(".csel-menu")) return;
      closeAllMenus();
    }, true);
    window.addEventListener("resize", () => closeAllMenus());
  }
  return enh;
}
function enhanceIn(root) { root.querySelectorAll("select").forEach(enhanceSelect); }
function syncSelects() { CSELECTS.forEach((e) => e.sync()); }
function setSelVisible(sel, show) { const w = sel._enh ? sel._enh.wrap : sel; if (w) w.style.display = show ? "" : "none"; }

// The profile stores the action fields next to the type ({type:"open", target:"..."}).
// The nested "params" that versions up to 0.4.0 wrote is still accepted when reading.
function actionParams(a) {
  const out = {};
  for (const k in a) if (k !== "type" && k !== "params") out[k] = a[k];
  return Object.assign(out, a.params || {});
}

function summary(a) {
  const p = actionParams(a);
  switch (a.type) {
    case "unassigned": return "\u2014";
    case "run": return p.cmd || (p.args || []).join(" ") || "script";
    case "open": return p.target || tr("type_open");
    case "text": return p.text || tr("type_text");
    case "media": case "native": return p.key || "media";
    case "hotkey": return p.send || tr("type_hotkey");
    case "window": return p.do || "window";
    case "sequence": return tr("type_sequence");
    default: return a.type;
  }
}

// --- i18n -----------------------------------------------------------------
function detectLang() {
  const saved = localStorage.getItem("hkc-lang");
  if (saved) return saved;
  for (const l of (navigator.languages || [navigator.language || "es"])) {
    const s = l.toLowerCase();
    if (s.startsWith("en")) return "en";
    if (s.startsWith("es")) return "es";
  }
  return "es";
}
function applyLang(lang) {
  LANG = lang; document.documentElement.lang = lang;
  document.querySelectorAll("[data-en]").forEach((el) => {
    if (el.dataset.es === undefined) el.dataset.es = el.innerHTML;
    el.innerHTML = lang === "en" ? el.dataset.en : el.dataset.es;
  });
  $("langBtnTxt").textContent = lang === "es" ? "English" : "Español";
  localStorage.setItem("hkc-lang", lang);
  if (state.profile) renderAll();
  refreshUpdateBar();
  syncSelects();
}

// --- editor modal ---------------------------------------------------------
let edState = null;
// binding = control completo (tiene .action y .color). Para los atajos del teclado
// normal no hay luz, asi que se puede pasar solo la accion.
function openEditor(binding, title, onSave) {
  const action = binding.action || binding;
  const hasColor = !!binding.action;   // solo los controles del macropad tienen luz
  edState = { work: { type: action.type, params: actionParams(action) },
              target: action, binding: hasColor ? binding : null, onSave };
  $("edTitle").textContent = title;
  $("edColorRow").style.display = hasColor ? "" : "none";
  if (hasColor) {
    const cur = binding.color || "";
    $("edColor").innerHTML = `<option value="">${tr("no_color")}</option>` +
      LED_COLOR_KEYS.map((k) => `<option value="${k}" data-color="${LED_HEX[k]}" ${k === cur ? "selected" : ""}>${tr(k)}</option>`).join("");
  }
  $("edType").innerHTML = ORDER.map((t) => `<option value="${t}" data-color="${TYPE_COLOR[t]}" ${t === action.type ? "selected" : ""}>${tr("type_" + t)}</option>`).join("");
  renderEdFields();
  $("edOverlay").classList.add("show");
  enhanceIn($("edColorRow"));
  if (edState.binding) $("edColor")._enh && $("edColor")._enh.sync();
}
function renderEdFields() {
  const t = edState.work.type;
  $("edHint").textContent = tr("hint_" + t);
  const fields = TYPE_FIELDS[t] || [];
  $("edFields").innerHTML = fields.map((f) => {
    const val = edState.work.params[f.k] != null ? edState.work.params[f.k] : "";
    const lbl = tr("fld_" + f.k);
    if (f.list) {  // opciones que salen del sistema (navegadores instalados)
      const items = f.list();
      return `<label>${lbl}</label><select data-f="${f.k}">${items.map((o) => `<option value="${esc(o.v)}" ${o.v === val ? "selected" : ""}>${esc(o.l)}</option>`).join("")}</select>`;
    }
    if (f.opts) return `<label>${lbl}</label><select data-f="${f.k}">${f.opts.map((o) => `<option value="${o}" ${o === val ? "selected" : ""}>${o}</option>`).join("")}</select>`;
    return `<label>${lbl}</label><input data-f="${f.k}" value="${esc(val)}" placeholder="${esc(f.ph || "")}">`;
  }).join("");
  $("edFields").querySelectorAll("[data-f]").forEach((el) => el.addEventListener("input", () => {
    if (el.value === "") delete edState.work.params[el.dataset.f]; else edState.work.params[el.dataset.f] = el.value;
  }));
  enhanceIn($("edFields"));
}
function closeEditor() { closeAllMenus(); $("edOverlay").classList.remove("show"); edState = null; }

// --- confirmación propia (sustituye al confirm() nativo) ------------------
let confirmResolve = null;
function confirmDialog(msg) {
  return new Promise((resolve) => {
    confirmResolve = resolve;
    $("confirmMsg").innerHTML = msg;
    $("confirmOverlay").classList.add("show");
  });
}

// --- captura de tecla -----------------------------------------------------
let capResolve = null, capValue = "";
function captureKey(titleKey) {
  return new Promise((resolve) => {
    capResolve = resolve; capValue = "";
    $("capTitle").textContent = tr(titleKey); $("capBox").textContent = tr("cap_waiting");
    $("capOverlay").classList.add("show");
  });
}
function keyName(e) {
  const c = e.code;
  if (/^Key[A-Z]$/.test(c)) return c.slice(3).toLowerCase();
  if (/^Digit\d$/.test(c)) return c.slice(5);
  if (/^F\d{1,2}$/.test(c)) return c.toLowerCase();
  const map = { Space: "space", Escape: "esc", Enter: "enter", Tab: "tab", Backspace: "backspace", Delete: "delete", ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right", Minus: "-", Equal: "=", Comma: ",", Period: ".", Slash: "/", Semicolon: ";", CapsLock: "caps lock", Home: "home", End: "end", PageUp: "page up", PageDown: "page down", Insert: "insert" };
  return map[c] || e.key.toLowerCase();
}
function onCaptureKeydown(e) {
  if (!$("capOverlay").classList.contains("show")) return;
  e.preventDefault();
  const mods = [];
  if (e.ctrlKey) mods.push("ctrl"); if (e.altKey) mods.push("alt"); if (e.shiftKey) mods.push("shift"); if (e.metaKey) mods.push("windows");
  if (["Control", "Alt", "Shift", "Meta"].includes(e.key)) { $("capBox").textContent = (mods.join("+") || "\u2026") + "+"; return; }
  capValue = [...mods, keyName(e)].join("+");
  $("capBox").textContent = capValue;
}

// --- render macropad ------------------------------------------------------
function gridDims(rows, cols, o) { return (o === "clockwise" || o === "counterclockwise") ? { r: cols, c: rows } : { r: rows, c: cols }; }
function cellIndex(dr, dc, rows, cols, o) {
  if (o === "upsidedown") return (rows - 1 - dr) * cols + (cols - 1 - dc);
  if (o === "clockwise") return (rows - 1 - dc) * cols + dr;
  if (o === "counterclockwise") return dc * cols + (cols - 1 - dr);
  return dr * cols + dc;
}
function renderLayers() { $("layers").innerHTML = state.profile.layers.map((l, i) => `<div class="lt ${i === state.layer ? "active" : ""}" data-l="${i}">${tr("key_word") === "Key" ? "Layer" : "Capa"} ${i + 1}</div>`).join(""); }
function renderLed() {
  const led = state.profile.layers[state.layer].led || { mode: "keep", color: "blue" };
  $("ledMode").innerHTML = LED_MODE_KEYS.map((k) => `<option value="${k}" ${k === led.mode ? "selected" : ""}>${tr("led_" + k)}</option>`).join("");
  $("ledColor").innerHTML = LED_COLOR_KEYS.map((k) => `<option value="${k}" data-color="${LED_HEX[k]}" ${k === led.color ? "selected" : ""}>${tr(k)}</option>`).join("");
  const show = led.mode !== "keep" && led.mode !== "off";
  setSelVisible($("ledColor"), show); $("ledSwatch").style.display = show ? "" : "none";
  $("ledSwatch").style.background = LED_HEX[led.color] || "#888";
}
function renderLayoutBar() {
  const d = state.profile.device;
  $("lbRows").textContent = d.rows; $("lbCols").textContent = d.columns; $("lbKnobs").textContent = d.knobs;
  $("lbOrient").innerHTML = ORIENT_KEYS.map((k) => `<option value="${k}" ${k === d.orientation ? "selected" : ""}>${tr("or_" + k)}</option>`).join("");
  const side = d.knob_side || "top";
  $("lbSide").innerHTML = SIDE_KEYS.map((k) => `<option value="${k}" ${k === side ? "selected" : ""}>${tr("side_" + k)}</option>`).join("");
  // Sin perillas no hay nada que colocar. Se oculta el contenedor por id: el padre
  // del select es el envoltorio que le pone el desplegable propio.
  $("lbSideWrap").style.display = d.knobs ? "" : "none";
  renderModelBar();
}
function renderPad() {
  const dev = state.profile.device, layer = state.profile.layers[state.layer];
  $("pad").className = "pad side-" + (dev.knob_side || "top");
  const subs = [["ccw", tr("knob_ccw")], ["press", tr("knob_press")], ["cw", tr("knob_cw")]];
  $("knobs").innerHTML = layer.knobs.map((kn, ki) => `
    <div class="knob">
      <div class="khead"><div class="circle">${svg("media")}</div><div class="klabel">${tr("knob_word")} ${ki + 1}</div></div>
      <div class="chips">${subs.map(([s, lbl]) => {
        const txt = summary(kn[s].action);
        return `<div class="chip" data-knob="${ki}" data-sub="${s}"><span class="cl">${lbl}</span><span class="cv">${esc(txt === "—" ? "" : txt)}</span></div>`;
      }).join("")}</div>
    </div>`).join("");
  const dims = gridDims(dev.rows, dev.columns, dev.orientation), g = $("grid");
  g.style.gridTemplateColumns = `repeat(${dims.c}, minmax(74px, 96px))`;
  let cells = "";
  for (let dr = 0; dr < dims.r; dr++) for (let dc = 0; dc < dims.c; dc++) {
    const i = cellIndex(dr, dc, dev.rows, dev.columns, dev.orientation), b = layer.buttons[i];
    if (!b) continue;
    const a = b.action, empty = a.type === "unassigned", col = TYPE_COLOR[a.type];
    const led = b.color ? `<span class="ledtag" style="background:${LED_HEX[b.color]}" title="${tr(b.color)}"></span>` : "";
    cells += `<div class="key ${empty ? "empty" : ""}" data-key="${i}" style="${empty ? "" : `border-color:${col}`}">
      <div class="kn">T${i + 1}${led}</div><div class="ic" style="color:${empty ? "var(--muted)" : col}">${svg(a.type)}</div>
      <div class="kv">${esc(summary(a))}</div></div>`;
  }
  g.innerHTML = cells;
}

function renderHotkeys() {
  const hk = state.profile.hotkeys || (state.profile.hotkeys = []);
  $("hotkeys").innerHTML = hk.length ? hk.map((h, i) => `<div class="item"><span class="kbd">${esc(h.combo)}</span><span class="desc">${esc(summary(h.action))}</span><button class="btn" data-edit="${i}" style="padding:5px 10px">${tr("edit")}</button><button class="x" data-del="${i}">\u2715</button></div>`).join("") : `<p style="color:var(--muted);font-size:13px">${tr("none_hotkeys")}</p>`;
}
function renderRemaps() {
  const rm = state.profile.remaps || (state.profile.remaps = []);
  $("remaps").innerHTML = rm.length ? rm.map((r, i) => `<div class="item"><span class="kbd">${esc(r.from)}</span><span style="color:var(--muted)">\u2192</span><span class="kbd">${esc(r.to)}</span><span class="desc"></span><button class="x" data-delr="${i}">\u2715</button></div>`).join("") : `<p style="color:var(--muted);font-size:13px">${tr("none_remaps")}</p>`;
}
function renderSteps() {
  $("steps").innerHTML = T[LANG].steps.map((s, i) => `<div class="step"><div class="num">${i + 1}</div><div class="st"><div class="t">${s.t}</div>${s.b}</div></div>`).join("");
}
function renderAll() { renderLayers(); renderLed(); renderLayoutBar(); renderPad(); renderHotkeys(); renderRemaps(); renderSteps(); }

let toastT;
function toast(msg, kind) { const t = $("toast"); t.textContent = msg; t.className = "toast show " + (kind || ""); clearTimeout(toastT); toastT = setTimeout(() => (t.className = "toast"), 2600); }
function setListenerBtn() { const b = $("listenBtn"); b.querySelector("span").textContent = state.listener ? tr("listen_stop") : tr("listen_start"); b.querySelector("svg").innerHTML = state.listener ? '<rect x="6" y="5" width="4" height="14"/><rect x="14" y="5" width="4" height="14"/>' : '<path d="M8 5v14l11-7z"/>'; }
async function pollStatus() {
  try {
    const s = await api().status(); state.listener = s.listener;
    $("devPill").className = "pill" + (s.connected ? " on" : "");
    // Un teclado reconocido pero de una familia sin soporte no es "desconectado":
    // decirlo asi manda al usuario a revisar un cable que esta perfecto.
    $("devTxt").textContent = s.connected ? tr("connected")
      : (s.unsupported ? tr("dev_unsupported") : tr("disconnected"));
    $("lbUsb").textContent = s.usb || "";
    setListenerBtn();
  } catch (e) { /* */ }
}
function refreshUpdateBar() {
  const u = state.update; if (!u || !u.update_available) return;
  $("updateText").textContent = tr("version_available").replace("{v}", u.latest);
  $("updateBtn").textContent = u.can_auto_install ? tr("update_now") : tr("download");
}
async function checkUpdate() {
  try {
    const u = await api().check_update();
    if (u && u.update_available) { state.update = u; $("updateBar").classList.add("show"); refreshUpdateBar(); }
  } catch (e) { /* sin conexión: silencioso */ }
}
function switchSection(sec) {
  state.section = sec;
  document.querySelectorAll(".nav .tab").forEach((t) => t.classList.toggle("active", t.dataset.sec === sec));
  document.querySelectorAll(".section").forEach((s) => s.classList.toggle("active", s.id === "sec-" + sec));
}

// --- tour interactivo con foco -------------------------------------------
const TOUR = [
  { sec: "pad", sel: "#flashBtn" },
  { sec: "pad", sel: ".grid .key" },
  { sec: "keys", sel: "#addHotkey" },
  { sec: "pad", sel: "#listenBtn" },
  { sec: "pad", sel: ".layoutbar" },
];
let tourStep = 0, tourOn = false;
function startTour() { tourOn = true; tourStep = 0; showTourStep(); }
function endTour() { tourOn = false; $("tourSpot").classList.remove("show"); $("tourPop").classList.remove("show"); localStorage.setItem("hkc-seen", "1"); }
function showTourStep() {
  const step = TOUR[tourStep];
  switchSection(step.sec);
  requestAnimationFrame(() => requestAnimationFrame(() => {
    if (!tourOn) return;
    const el = document.querySelector(step.sel);
    if (!el) { if (tourStep < TOUR.length - 1) { tourStep++; showTourStep(); } else endTour(); return; }
    el.scrollIntoView({ block: "center" });
    const r = el.getBoundingClientRect(), pad = 6, spot = $("tourSpot");
    spot.style.top = (r.top - pad) + "px"; spot.style.left = (r.left - pad) + "px";
    spot.style.width = (r.width + pad * 2) + "px"; spot.style.height = (r.height + pad * 2) + "px";
    spot.classList.add("show");
    const txt = T[LANG].steps[tourStep];
    $("tourNum").textContent = `${tourStep + 1} / ${TOUR.length}`;
    $("tourTitle").textContent = txt.t; $("tourBody").innerHTML = txt.b;
    $("tourBack").style.visibility = tourStep === 0 ? "hidden" : "visible";
    $("tourNext").textContent = tourStep === TOUR.length - 1 ? (LANG === "en" ? "Finish" : "Fin") : (LANG === "en" ? "Next" : "Siguiente");
    const pop = $("tourPop"); pop.classList.add("show");
    const ph = pop.offsetHeight || 170, pw = 300;
    let top = r.bottom + 12; if (top + ph > window.innerHeight - 8) top = Math.max(8, r.top - 12 - ph);
    let left = r.left; if (left + pw > window.innerWidth - 8) left = window.innerWidth - pw - 8; if (left < 8) left = 8;
    pop.style.top = top + "px"; pop.style.left = left + "px";
  }));
}

// --- modelo de teclado ----------------------------------------------------
// Se elige el teclado que uno tiene, no unas medidas libres: un macropad de 7x9
// no existe, y configurarlo solo lleva a una decepcion. Los deslizantes siguen
// ahi para variantes raras, detras de "Otro (a medida)".
function modelName(m) {
  if (m.id === CUSTOM_ID) return tr("model_custom");
  const keys = m.keys + " " + tr("u_keys");
  if (!m.knobs) return keys;
  return keys + " " + tr("u_and") + " " + m.knobs + " " + tr(m.knobs === 1 ? "u_knob" : "u_knobs");
}

function renderModelBar() {
  const d = state.profile.device;
  const sel = $("lbModel");
  const opciones = MODELS.concat([{ id: CUSTOM_ID }]);
  sel.innerHTML = opciones.map((m) => {
    const marca = m.supported === false ? " • " + tr("model_pending") : "";
    return `<option value="${m.id}" ${m.id === d.model ? "selected" : ""}>${esc(modelName(m) + marca)}</option>`;
  }).join("");   // el enhancer se resincroniza solo al cambiar los options
  $("lbCustom").style.display = d.model === CUSTOM_ID ? "" : "none";
  const actual = MODELS.filter((m) => m.id === d.model)[0];
  $("lbNote").textContent = actual && actual.note ? tr(actual.note) : "";
}

async function pickModel(id) {
  const d = state.profile.device;
  if (id === d.model) return;
  if (id === CUSTOM_ID) { d.model = id; markDirty(); renderModelBar(); return; }
  const m = MODELS.filter((x) => x.id === id)[0];
  if (!m) return;
  const igual = m.rows === d.rows && m.columns === d.columns && m.knobs === d.knobs;
  if (!igual && !(await confirmDialog(tr("confirm_layout")))) { renderModelBar(); return; }
  if (!igual) {
    state.profile = await api().resize_layout(state.profile, m.rows, m.columns, m.knobs, d.orientation);
    if (state.layer >= state.profile.layers.length) state.layer = 0;
  }
  state.profile.device.model = id;
  markDirty(); renderAll();
  if (!igual) toast(tr("layout_applied"), "ok");
}

// --- layout inline --------------------------------------------------------
async function changeLayout(dim, delta) {
  const d = state.profile.device;
  let rows = d.rows, cols = d.columns, knobs = d.knobs;
  if (dim === "rows") rows = Math.max(1, Math.min(5, rows + delta));
  if (dim === "cols") cols = Math.max(1, Math.min(5, cols + delta));
  if (dim === "knobs") knobs = Math.max(0, Math.min(4, knobs + delta));
  if (rows === d.rows && cols === d.columns && knobs === d.knobs) return;
  if (rows * cols > 15 || (knobs > 3 && rows * cols > 12)) { toast(LANG === "en" ? "Beyond ch57x limits" : "Fuera del l\u00edmite ch57x", "err"); return; }
  if (!(await confirmDialog(tr("confirm_layout")))) return;
  state.profile = await api().resize_layout(state.profile, rows, cols, knobs, d.orientation);
  if (state.layer >= state.profile.layers.length) state.layer = 0;
  markDirty(); renderAll(); toast(tr("layout_applied"), "ok");
}

function wire() {
  $("nav").addEventListener("click", (e) => { const t = e.target.closest(".tab"); if (t) switchSection(t.dataset.sec); });
  $("guideBtn").onclick = startTour;
  $("startTour").onclick = startTour;
  $("updateBtn").onclick = async () => {
    const u = state.update; if (!u) return;
    if (u.can_auto_install) { toast(tr("updating")); const r = await api().apply_update(); if (!r.ok) toast(tr("err") + ": " + r.error, "err"); }
    else api().open_url(u.notes_url);
  };
  $("updateNotes").onclick = () => { if (state.update) api().open_url(state.update.notes_url); };
  $("updateClose").onclick = () => $("updateBar").classList.remove("show");
  $("tourNext").onclick = () => { if (tourStep < TOUR.length - 1) { tourStep++; showTourStep(); } else endTour(); };
  $("tourBack").onclick = () => { if (tourStep > 0) { tourStep--; showTourStep(); } };
  $("tourSkip").onclick = endTour;
  window.addEventListener("resize", () => { if (tourOn) showTourStep(); });
  $("langBtn").onclick = () => applyLang(LANG === "es" ? "en" : "es");
  $("layers").addEventListener("click", (e) => { const t = e.target.closest(".lt"); if (t) { state.layer = +t.dataset.l; renderLayers(); renderLed(); renderPad(); } });
  $("grid").addEventListener("click", (e) => { const k = e.target.closest(".key"); if (!k) return; const b = state.profile.layers[state.layer].buttons[+k.dataset.key]; openEditor(b, `${tr("key_word")} ${+k.dataset.key + 1}`, () => { markDirty(); renderPad(); }); });
  $("knobs").addEventListener("click", (e) => { const c = e.target.closest(".chip"); if (!c) return; const b = state.profile.layers[state.layer].knobs[+c.dataset.knob][c.dataset.sub]; openEditor(b, `${tr("knob_word")} ${+c.dataset.knob + 1}`, () => { markDirty(); renderPad(); }); });
  $("ledMode").onchange = setLed; $("ledColor").onchange = setLed;

  document.querySelector(".layoutbar").addEventListener("click", (e) => { const b = e.target.closest("[data-d]"); if (b) changeLayout(b.dataset.d, +b.dataset.v); });
  $("lbOrient").onchange = (e) => { state.profile.device.orientation = e.target.value; markDirty(); renderPad(); };
  $("lbModel").onchange = (e) => pickModel(e.target.value);
  $("lbSide").onchange = (e) => { state.profile.device.knob_side = e.target.value; markDirty(); renderPad(); };

  $("addHotkey").onclick = async () => { const combo = await captureKey("cap_shortcut"); if (!combo) return; const h = { combo, action: { type: "unassigned" } }; state.profile.hotkeys.push(h); markDirty(); renderHotkeys(); openEditor(h.action, combo, () => { markDirty(); renderHotkeys(); }); };
  $("hotkeys").addEventListener("click", (e) => { const ed = e.target.closest("[data-edit]"), del = e.target.closest("[data-del]"); if (ed) { const h = state.profile.hotkeys[+ed.dataset.edit]; openEditor(h.action, h.combo, () => { markDirty(); renderHotkeys(); }); } if (del) { state.profile.hotkeys.splice(+del.dataset.del, 1); markDirty(); renderHotkeys(); } });
  $("addRemap").onclick = async () => { const from = await captureKey("cap_from"); if (!from) return; const to = await captureKey("cap_to"); if (!to) return; state.profile.remaps.push({ from, to }); markDirty(); renderRemaps(); };
  $("remaps").addEventListener("click", (e) => { const del = e.target.closest("[data-delr]"); if (del) { state.profile.remaps.splice(+del.dataset.delr, 1); markDirty(); renderRemaps(); } });

  $("edType").onchange = (e) => { edState.work.type = e.target.value; edState.work.params = {}; renderEdFields(); };
  $("edSave").onclick = () => {
    const a = edState.target, w = edState.work;
    for (const k in a) if (k !== "type") delete a[k];   // out with the previous fields
    a.type = w.type; Object.assign(a, w.params);        // flat, the shape the listener reads
    if (edState.binding) {
      const c = $("edColor").value;
      if (c) edState.binding.color = c; else delete edState.binding.color;
    }
    const cb = edState.onSave; closeEditor(); cb && cb();
  };
  $("edTest").onclick = async () => { const r = await api().test_action(edState.work); toast(r.ok ? tr("executed") : tr("err") + ": " + r.error, r.ok ? "ok" : "err"); };
  $("edCancel").onclick = closeEditor;

  window.addEventListener("keydown", onCaptureKeydown, true);
  $("capOk").onclick = () => { $("capOverlay").classList.remove("show"); const r = capResolve; capResolve = null; r && r(capValue || ""); };
  $("capCancel").onclick = () => { $("capOverlay").classList.remove("show"); const r = capResolve; capResolve = null; r && r(""); };
  $("confirmYes").onclick = () => { $("confirmOverlay").classList.remove("show"); const r = confirmResolve; confirmResolve = null; r && r(true); };
  $("confirmNo").onclick = () => { $("confirmOverlay").classList.remove("show"); const r = confirmResolve; confirmResolve = null; r && r(false); };

  $("saveBtn").onclick = async () => { const r = await api().save_profile(state.profile); if (r.ok) { state.dirty = false; toast(tr("saved"), "ok"); if (state.listener) { await api().stop_listener(); await api().start_listener(); } } else toast(tr("err") + ": " + r.error, "err"); };
  $("flashBtn").onclick = async () => { if (!(await confirmDialog(tr("confirm_flash")))) return; toast(tr("flashing")); const r = await api().flash(state.profile); toast(r.ok ? `${tr("flashed")} (${r.n})` : tr("err") + ": " + r.error, r.ok ? "ok" : "err"); };
  $("listenBtn").onclick = async () => { const r = state.listener ? await api().stop_listener() : await api().start_listener(); state.listener = r.listener; setListenerBtn(); toast(state.listener ? tr("listener_on") : tr("listener_off"), "ok"); };
}
function setLed() { const mode = $("ledMode").value, color = $("ledColor").value; state.profile.layers[state.layer].led = (mode === "keep") ? null : { mode, color }; markDirty(); renderLed(); }

async function init() {
  state.profile = await api().get_profile();
  try { BROWSERS = await api().browsers() || []; } catch (e) { BROWSERS = []; }
  try { MODELS = await api().models() || []; } catch (e) { MODELS = []; }
  wire(); enhanceIn(document); applyLang(detectLang()); setListenerBtn(); pollStatus(); setInterval(pollStatus, 3000);
  checkUpdate();
  // El tour no se lanza solo al abrir (molestaba en cada arranque). Esta a un clic
  // en la pestana "Guia" -> "Iniciar tour interactivo", o en el boton "Guia" de la cabecera.
}
if (window.pywebview && window.pywebview.api) init();
else window.addEventListener("pywebviewready", init);
