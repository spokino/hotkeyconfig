# FEEDBACK.md - Registro Continuo de Desarrollo y Memoria Viva

Este documento actúa como la memoria viva de este proyecto. Registra los desafíos técnicos, bugs difíciles, fallos de build y soluciones encontradas durante nuestras sesiones de desarrollo con IA para evitar repetir los mismos errores en el futuro.

---
## 🔍 Registro de Retos y Errores Resueltos
*(La IA registrará aquí automáticamente cada bug o problema técnico superado durante el desarrollo).*

### 2026-07-22 | El flasheo por libusb no funciona en Windows
**Problema:** `ch57x-keyboard-tool upload` fallaba con `Error: find USB device / Entity not found`,
aunque `validate` pasaba y el dispositivo `1189:8842` estaba conectado y visible.
**Causa:** la herramienta usa `rusb` (libusb). En Windows, libusb no puede abrir un dispositivo
que está tomado por el driver HID nativo; requiere sustituir el driver con Zadig/UsbDk.
**Solución:** no tocar drivers. Se portó el protocolo k884x byte a byte a `protocol.py` y se envía
por la API HID nativa de Windows (`hidapi`) en `hid_flasher.py`, escribiendo en la interfaz de
programación `MI_00` (usage page `0xFF00`). Resultado: cero drivers, cero Rust, instalación solo con pip.

### 2026-07-22 | Framing del reporte HID: `WriteFile 0x57 parámetro no es correcto`
**Problema:** las escrituras HID devolvían -1 con `WriteFile: (0x00000057)`.
**Causa:** se asumió que los mensajes de 64 bytes de ch57x eran datos sin numerar y se anteponía
`0x00` como Report ID. Falso: el `0x03` inicial de cada mensaje ES el Report ID.
**Diagnóstico:** leer las HID caps con ctypes (`HidP_GetCaps`) dio `OutputReportByteLength = 65`
y cero feature reports; una sonda probando variantes de framing confirmó cuál aceptaba el dispositivo.
**Solución:** escribir `report = mensaje_64 + b"\x00"` (65 bytes), con el `0x03` como primer byte.
El mensaje `init` (64 ceros) no es enviable por HID (Report ID 0 es inválido) y se omite.
Sondas de diagnóstico conservadas en `scripts/_probe_caps.py` y `_probe_write.py`.

### 2026-07-22 | `keyboard.unhook_all_hotkeys()` peta en el primer arranque
**Problema:** `AttributeError: '_KeyboardListener' object has no attribute 'blocking_hotkeys'`
al iniciar el listener por primera vez.
**Causa:** bug de la librería `keyboard` 0.13.5; ese atributo no existe hasta que se registra el
primer hotkey, y el runtime llamaba a `unhook_all_hotkeys()` antes para limpiar.
**Solución:** envolver la llamada en `try/except (AttributeError, KeyError)` en `runtime.py`.

### 2026-07-22 | La config de ch57x 1.7.0 no lleva campo `model`
**Problema:** el `example-mapping.yaml` del repo incluye `model: ch57x-2`, pero al usarlo la
versión publicada podía rechazarlo.
**Causa:** ese ejemplo es de la rama `master`, no de la 1.7.0 publicada en crates.io. En 1.7.0 el
struct `Config` solo tiene `orientation`, `rows`, `columns`, `knobs` y `layers`.
**Solución:** generar el YAML sin `model`, con los botones como filas x columnas.
