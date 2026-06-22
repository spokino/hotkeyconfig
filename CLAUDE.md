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
- `protocol.py` — **constructor de los mensajes USB k884x** (portado byte a byte
  desde ch57x). `build_messages(profile)` -> lista de mensajes de 64 bytes.
- `hid_flasher.py` — **flasher por HID nativo (por defecto)**: abre MI_00 y escribe.
- `flasher.py` — backend ALTERNATIVO opcional (binario ch57x por stdin).
- `runtime.py` — registra atajos globales y despacha acciones; recarga en caliente.
- `actions.py` — ejecutores: run/open/text/media/hotkey/window/sequence/native.
- `tray.py` — icono de bandeja (pausar/recargar/editar/salir).
- `autostart.py` — acceso directo en shell:startup (`pythonw -m hotkeyconfig run`).
- `cli.py` — `detect | generate | flash | run | autostart`.

## Detalles que importan (HID)
- Dispositivo `1189:8842` = familia **k884x**. Interfaz de programación = **MI_00**,
  `usage_page=0xFF00`. La de escritura es MI_01 (no se toca).
- **Framing HID confirmado** leyendo HID caps: `OutputReportByteLength=65`, sin
  feature reports. El `0x03` inicial de cada mensaje ch57x es el **Report ID**, no
  datos. Por eso se escribe `report = mensaje_64 + b"\x00"` (65 bytes); NO anteponer
  `0x00` (eso da "parámetro incorrecto"). El mensaje init (todo ceros) se **omite**.
- key_id: botones 1..12; perilla k (0-based) acción ccw/press/cw -> 16+3k+a.
- Modificadores: ctrl=1, shift=2, alt=4, win=8. F13=0x68..F24=0x73. Media: VolUp=0xe9,
  VolDown=0xea, Mute=0xe2, Play=0xcd, Next=0xb5, Prev=0xb6.
- ch57x binario (opcional): config 1.7.0 NO usa campo `model`; botones en filas×columnas.

## Cómo correr / probar
```bash
.venv\Scripts\hotkeyconfig detect
.venv\Scripts\hotkeyconfig generate
.venv\Scripts\hotkeyconfig flash      # ¡escribe en la memoria del HW! preguntar antes
.venv\Scripts\hotkeyconfig run
.venv\Scripts\hotkeyconfig autostart install
```
Sondas de diagnóstico en `scripts/_probe_caps.py` (lee HID caps) y `_probe_write.py`.

## Reglas
Ver `REGLAS.md` y `SECURITY.md`. Sin `Co-Authored-By`. Preguntar antes de push y
antes de `flash`. Dependencias mínimas, auditadas.
