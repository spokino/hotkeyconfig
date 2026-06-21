# CLAUDE.md — contexto del proyecto

## Qué es
`hotkeyconfig`: app open source (Python) para programar macropads **ch57x**
(p. ej. `1189:8842`, 12 teclas + 2 perillas + 3 capas) y asignar a cada control
un script/atajo. Une dos motores ya probados: `ch57x-keyboard-tool` (grabar el
HW) + librería `keyboard` (escuchar y actuar).

## Idea central
El teclado emite HID estándar, no IDs por tecla. Se asigna a cada control un
combo único e improbable (`F13`–`F24` + familias de modificadores por capa) →
**54 combos sin colisión**. El listener mapea combo → acción. Como cada combo es
único, el runtime **no** necesita seguir el estado de capa (lo conmuta el HW).

## Arquitectura (`hotkeyconfig/`)
- `combos.py` — layout del dispositivo + generador de combos únicos. `to_ch57x`
  / `to_keyboard` traducen la forma canónica a cada destino.
- `profile.py` — modelo de datos (`Profile/Layer/Binding/Action`) + load/save/validate.
- `flasher.py` — traduce el perfil al YAML de ch57x 1.7.0 y llama a `validate`/`upload`.
- `runtime.py` — registra atajos globales y despacha acciones; recarga en caliente.
- `actions.py` — ejecutores: run/open/text/media/hotkey/window/sequence/native.
- `tray.py` — icono de bandeja (pausar/recargar/editar/salir).
- `cli.py` — `detect | generate | flash | run`.

## Detalles que importan
- ch57x **1.7.0** (la instalada) NO usa el campo `model` (eso es de `master`).
  Config = `orientation/rows/columns/knobs/layers`; botones en **filas×columnas**.
- Modificadores ch57x: `ctrl/shift/alt/win` unidos con `-`. La librería `keyboard`
  usa `+` y `windows` en vez de `win`.
- Perillas por defecto: multimedia **nativo** (no pasa por el runtime).
- `cargo install ch57x-keyboard-tool --locked`; binario en `~/.cargo/bin`.

## Cómo correr / probar
```bash
.venv\Scripts\hotkeyconfig detect
.venv\Scripts\hotkeyconfig generate
.venv\Scripts\hotkeyconfig flash      # ¡escribe en el HW! preguntar antes
.venv\Scripts\hotkeyconfig run
```

## Reglas
Ver `REGLAS.md` y `SECURITY.md`. Sin `Co-Authored-By`. Preguntar antes de push y
antes de `flash`. Dependencias mínimas, auditadas.
