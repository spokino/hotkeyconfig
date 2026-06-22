"use strict";

const MEDIA_KEYS = ["volume_up", "volume_down", "mute", "play_pause", "next", "previous", "stop"];
const WINDOW_OPS = ["minimize", "maximize", "restore", "close"];

const ICONS = {
  unassigned: '<path d="M12 5v14M5 12h14"/>',
  run: '<path d="M4 6l5 6-5 6"/><path d="M12 18h8"/>',
  open: '<path d="M14 4h6v6"/><path d="M20 4L10 14"/><path d="M18 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h6"/>',
  text: '<path d="M4 6h16M4 12h10M4 18h7"/>',
  media: '<path d="M11 5L6 9H3v6h3l5 4z"/><path d="M16 9a4 4 0 0 1 0 6"/>',
  native: '<path d="M11 5L6 9H3v6h3l5 4z"/><path d="M16 9a4 4 0 0 1 0 6"/>',
  hotkey: '<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/>',
  window: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/>',
  sequence: '<path d="M9 6h12M9 12h12M9 18h12M4 6h.01M4 12h.01M4 18h.01"/>',
};

const TYPES = {
  unassigned: { label: "Sin asignar", color: "var(--muted)", fields: [], hint: "No hace nada (manda su combo único listo para asignar)." },
  run: { label: "Ejecutar script / comando", color: "var(--c-run)", hint: "Lanza un .py / .ps1 / .bat / programa con argumentos.",
    fields: [{ k: "cmd", l: "Comando", ph: "py C:/scripts/deploy.py" }, { k: "cwd", l: "Carpeta (opcional)", ph: "" }] },
  open: { label: "Abrir app / carpeta / URL", color: "var(--c-open)", hint: "Abre un programa, una carpeta o una página web.",
    fields: [{ k: "target", l: "Destino", ph: "https://github.com/Mun1to" }] },
  text: { label: "Escribir texto", color: "var(--c-text)", hint: "Escribe el texto al pulsar (snippets, plantillas…).",
    fields: [{ k: "text", l: "Texto", ph: "Hola desde mi macropad" }] },
  media: { label: "Multimedia (vía app)", color: "var(--c-media)", hint: "Tecla multimedia gestionada por el listener.",
    fields: [{ k: "key", l: "Tecla", opts: MEDIA_KEYS }] },
  native: { label: "Multimedia nativo (en el teclado)", color: "var(--c-native)", hint: "Se graba en el teclado: funciona aunque la app no esté abierta. Requiere reflashear.",
    fields: [{ k: "key", l: "Tecla", opts: MEDIA_KEYS }] },
  hotkey: { label: "Enviar atajo", color: "var(--c-hotkey)", hint: "Manda un atajo a la app activa, p. ej. ctrl+c.",
    fields: [{ k: "send", l: "Atajo", ph: "ctrl+shift+s" }] },
  window: { label: "Ventana activa", color: "var(--c-window)", hint: "Minimiza / maximiza / restaura / cierra la ventana activa.",
    fields: [{ k: "do", l: "Operación", opts: WINDOW_OPS }] },
  sequence: { label: "Secuencia", color: "var(--c-sequence)", fields: [], hint: "Varias acciones en orden (se edita en profile.yaml por ahora)." },
};
const ORDER = ["unassigned", "run", "open", "text", "media", "native", "hotkey", "window", "sequence"];

const state = { profile: null, layer: 0, sel: null, dirty: false, listener: false };

const $ = (id) => document.getElementById(id);
const api = () => window.pywebview.api;
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const svg = (type) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[type] || ICONS.unassigned}</svg>`;

function summary(a) {
  const p = a.params || a;
  switch (a.type) {
    case "unassigned": return "—";
    case "run": return p.cmd || (p.args || []).join(" ") || "script";
    case "open": return p.target || "abrir";
    case "text": return p.text || "texto";
    case "media": case "native": return p.key || "media";
    case "hotkey": return p.send || "atajo";
    case "window": return p.do || "ventana";
    case "sequence": return "secuencia";
    default: return a.type;
  }
}

function bindingAt(sel) {
  const L = state.profile.layers[sel.layer];
  return sel.kind === "button" ? L.buttons[sel.index] : L.knobs[sel.knob][sel.sub];
}
function isSel(kind, a, b) {
  const s = state.sel;
  if (!s || s.layer !== state.layer || s.kind !== kind) return false;
  return kind === "button" ? s.index === a : (s.knob === a && s.sub === b);
}

function renderTabs() {
  $("tabs").innerHTML = state.profile.layers.map((l, i) =>
    `<div class="tab ${i === state.layer ? "active" : ""}" data-layer="${i}">Capa ${i + 1}</div>`).join("");
}

function renderPad() {
  const L = state.profile.layers[state.layer];
  const subs = [["ccw", "◀ izq."], ["press", "● pulsar"], ["cw", "der. ▶"]];
  $("knobs").innerHTML = L.knobs.map((kn, ki) => `
    <div class="knob">
      <div class="circle">${svg("media")}</div>
      <div class="klabel">Perilla ${ki + 1}</div>
      <div class="chips">${subs.map(([s, lbl]) => {
        const a = kn[s].action;
        return `<div class="chip ${isSel("knob", ki, s) ? "sel" : ""}" data-knob="${ki}" data-sub="${s}">
          <span>${lbl}</span><span class="cv">${esc(summary(a))}</span></div>`;
      }).join("")}</div>
    </div>`).join("");

  $("grid").innerHTML = L.buttons.map((b, i) => {
    const a = b.action, empty = a.type === "unassigned", col = TYPES[a.type].color;
    return `<div class="key ${empty ? "empty" : ""} ${isSel("button", i) ? "sel" : ""}" data-key="${i}"
      style="${empty ? "" : `border-color:${col}`}">
      <div class="kn">T${i + 1}</div>
      <div class="ic" style="color:${empty ? "var(--muted)" : col}">${svg(a.type)}</div>
      <div class="kv">${esc(summary(a))}</div></div>`;
  }).join("");
}

function renderEditor() {
  const ed = $("editor");
  if (!state.sel) { ed.innerHTML = '<div class="placeholder">Haz clic en una tecla o en una acción de perilla para configurarla.</div>'; return; }
  const a = bindingAt(state.sel).action;
  const def = TYPES[a.type];
  const title = state.sel.kind === "button"
    ? `Tecla ${state.sel.index + 1}`
    : `Perilla ${state.sel.knob + 1} · ${({ ccw: "girar izq.", press: "pulsar", cw: "girar der." })[state.sel.sub]}`;
  const fields = def.fields.map((f) => {
    const val = (a.params && a.params[f.k] != null) ? a.params[f.k] : "";
    if (f.opts) {
      return `<label>${f.l}</label><select data-f="${f.k}">${f.opts.map((o) =>
        `<option value="${o}" ${o === val ? "selected" : ""}>${o}</option>`).join("")}</select>`;
    }
    return `<label>${f.l}</label><input data-f="${f.k}" value="${esc(val)}" placeholder="${esc(f.ph || "")}">`;
  }).join("");
  ed.innerHTML = `
    <h3>Control</h3>
    <div class="target" style="color:${def.color}">${svg(a.type)}<span style="color:var(--text)">${title}</span></div>
    <label>Acción</label>
    <select id="typeSel">${ORDER.map((t) => `<option value="${t}" ${t === a.type ? "selected" : ""}>${TYPES[t].label}</option>`).join("")}</select>
    <div id="fields">${fields}</div>
    <div class="hint">${def.hint}</div>`;

  $("typeSel").onchange = (e) => {
    const b = bindingAt(state.sel);
    b.action.type = e.target.value;
    b.action.params = {};
    state.dirty = true;
    renderEditor(); renderPad();
  };
  ed.querySelectorAll("[data-f]").forEach((el) => {
    const apply = () => {
      const b = bindingAt(state.sel);
      b.action.params = b.action.params || {};
      if (el.value === "") delete b.action.params[el.dataset.f];
      else b.action.params[el.dataset.f] = el.value;
      state.dirty = true;
    };
    el.addEventListener("input", apply);
    el.addEventListener("change", () => { apply(); renderPad(); });
  });
}

function render() { renderTabs(); renderPad(); renderEditor(); }

let toastT;
function toast(msg, kind) {
  const t = $("toast");
  t.textContent = msg; t.className = "toast show " + (kind || "");
  clearTimeout(toastT); toastT = setTimeout(() => (t.className = "toast"), 2600);
}

function setListenerBtn() {
  const b = $("listenBtn");
  b.querySelector("span").textContent = state.listener ? "Parar listener" : "Iniciar listener";
  b.querySelector("svg").innerHTML = state.listener
    ? '<rect x="6" y="5" width="4" height="14"/><rect x="14" y="5" width="4" height="14"/>'
    : '<path d="M8 5v14l11-7z"/>';
}

async function pollStatus() {
  try {
    const s = await api().status();
    state.listener = s.listener;
    $("devPill").className = "pill" + (s.connected ? " on" : "");
    $("devTxt").textContent = s.connected ? "teclado conectado" : "teclado no detectado";
    setListenerBtn();
  } catch (e) { /* webview aún no listo */ }
}

function wireEvents() {
  $("tabs").addEventListener("click", (e) => {
    const t = e.target.closest(".tab"); if (!t) return;
    state.layer = +t.dataset.layer; state.sel = null; render();
  });
  $("grid").addEventListener("click", (e) => {
    const k = e.target.closest(".key"); if (!k) return;
    state.sel = { layer: state.layer, kind: "button", index: +k.dataset.key }; render();
  });
  $("knobs").addEventListener("click", (e) => {
    const c = e.target.closest(".chip"); if (!c) return;
    state.sel = { layer: state.layer, kind: "knob", knob: +c.dataset.knob, sub: c.dataset.sub }; render();
  });
  $("themeBtn").onclick = () => {
    const cur = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", cur);
    localStorage.setItem("hkc-theme", cur);
  };
  $("saveBtn").onclick = async () => {
    const r = await api().save_profile(state.profile);
    if (r.ok) { state.dirty = false; toast("Guardado", "ok"); if (state.listener) { await api().stop_listener(); await api().start_listener(); } }
    else toast("Error: " + r.error, "err");
  };
  $("flashBtn").onclick = async () => {
    if (!confirm("Se grabarán los combos en la MEMORIA del teclado. ¿Continuar?")) return;
    toast("Flasheando…");
    const r = await api().flash(state.profile);
    toast(r.ok ? `Teclado grabado (${r.n} mensajes)` : "Error: " + r.error, r.ok ? "ok" : "err");
  };
  $("listenBtn").onclick = async () => {
    const r = state.listener ? await api().stop_listener() : await api().start_listener();
    state.listener = r.listener; setListenerBtn();
    toast(state.listener ? "Listener activo" : "Listener detenido", "ok");
  };
}

async function init() {
  document.documentElement.setAttribute("data-theme", localStorage.getItem("hkc-theme") || "dark");
  state.profile = await api().get_profile();
  wireEvents(); render(); setListenerBtn();
  pollStatus(); setInterval(pollStatus, 3000);
}

if (window.pywebview && window.pywebview.api) init();
else window.addEventListener("pywebviewready", init);
