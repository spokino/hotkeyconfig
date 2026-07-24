<p align="center">
  <img src="branding/logo-256.png" alt="hotkeyconfig" width="128" height="128">
</p>

<h1 align="center">hotkeyconfig</h1>

<p align="center">
  Convierte un macropad chino de 20 € en un panel de atajos donde cada tecla ejecuta lo que tú quieras.
</p>

<p align="center">
  <img alt="Licencia MIT" src="https://img.shields.io/badge/licencia-MIT-0B4FA4">
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-0B4FA4">
  <img alt="Windows" src="https://img.shields.io/badge/Windows-10%20%2F%2011-0B4FA4">
  <img alt="Sin drivers" src="https://img.shields.io/badge/sin%20Zadig%20%2F%20sin%20Rust-0B4FA4">
</p>

App **open source** y sencilla para convertir un macropad chino barato (los de
AliExpress basados en el chip **ch57x**, p. ej. `1189:8842`, de 12 teclas + 2
perillas + 3 capas) en un panel de atajos donde **cada tecla ejecuta el script
o la acción que tú quieras**.

> Programa el teclado **sin el software propietario** que viene en un Google
> Drive, desde un único archivo de configuración, y con un listener que no es un
> keylogger (ver [SECURITY.md](SECURITY.md)).

## ¿Por qué existe?

Estos macropads no exponen un identificador único por tecla: emiten pulsaciones
HID estándar. Para hacer cada tecla **única** hay que asignarle una combinación
que ningún teclado físico produce. `hotkeyconfig` usa las teclas fantasma
`F13`-`F24` con familias de modificadores distintas por capa, generando **54
combos únicos sin colisión** (12 teclas × 3 capas + 2 perillas × 3 acciones × 3
capas). Luego un proceso en segundo plano escucha esos combos y ejecuta tu acción.

### Dos mitades

1. **Grabar los combos únicos en el teclado**, por **HID nativo de Windows**, igual
   que el software propietario: **sin Zadig, sin drivers, sin Rust**. El protocolo
   está portado byte a byte desde [`kriomant/ch57x-keyboard-tool`](https://github.com/kriomant/ch57x-keyboard-tool)
   (que queda como backend alternativo opcional). Como el teclado tiene **memoria
   interna**, los combos persisten sin ningún software.
2. **Escuchar los combos y ejecutar acciones**, con un listener local que usa la librería
   [`keyboard`](https://pypi.org/project/keyboard/), en un icono de bandeja privado
   que puede **arrancar solo con Windows**.

## Instalación

Solo Python 3.11+ (nada de Rust):

```bash
python -m venv .venv
.venv\Scripts\pip install -e .
```

## Uso

```bash
hotkeyconfig detect              # ¿teclado conectado?
hotkeyconfig generate            # crea config/profile.yaml con 54 combos únicos
#   …edita profile.yaml y asigna acciones a tus teclas…
hotkeyconfig flash               # graba los combos en la memoria del teclado (HID)
hotkeyconfig run                 # escucha y ejecuta (icono en la bandeja)
hotkeyconfig autostart install   # que arranque solo al encender Windows
```

> La parte "única" de las teclas vive en la **memoria del teclado** (flasheo una vez,
> persiste). El listener solo hace falta para **ejecutar tus acciones**; es local y
> privado, y si no está de fondo simplemente esas acciones no se disparan.

## Compilar el ejecutable (.exe)

Genera una app de Windows autónoma (sin necesitar Python) e instalador, con
PyInstaller + Inno Setup:

```bash
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\python scripts/build.py              # dist\hotkeyconfig\hotkeyconfig.exe
.venv\Scripts\python scripts/build.py --installer  # + dist\hotkeyconfig-<version>-setup.exe
```

El instalador no pide administrador, crea accesos directos y una casilla para
arrancar con Windows. La configuración del usuario se guarda en
`%LOCALAPPDATA%\hotkeyconfig\profile.yaml`.

## Tipos de acción

| `type` | Qué hace | Campos |
|--------|----------|--------|
| `run` | Lanza script/comando | `cmd` o `args`, `cwd`, `shell` |
| `open` | Abre app, carpeta o URL | `target` |
| `text` | Escribe/pega texto | `text` |
| `media` | Tecla multimedia (vía app) | `key` |
| `hotkey` | Manda un atajo a la app activa | `send` |
| `window` | Minimiza/maximiza/cierra (pywin32) | `do` |
| `sequence` | Varias acciones en orden | `steps` |
| `native` | Se graba en el HW (volumen…) | `key` |
| `unassigned` | Sin asignar | (ninguno) |

Ejemplo (`config/profile.example.yaml`):

```yaml
layers:
  - name: "Capa 1"
    buttons:
      - combo: "ctrl+alt+f13"
        action: { type: run, cmd: "py C:/scripts/deploy.py" }
      - combo: "ctrl+alt+f14"
        action: { type: open, target: "https://github.com/Mun1to" }
    knobs:
      - ccw:   { combo: "ctrl+win+f13", action: { type: native, key: volume_down } }
        press: { combo: "ctrl+win+f14", action: { type: native, key: mute } }
        cw:    { combo: "ctrl+win+f15", action: { type: native, key: volume_up } }
```

## Layout (orientación normal)

```
 [ T1 ][ T2 ][ T3 ][ T4 ]      ( P1 )
 [ T5 ][ T6 ][ T7 ][ T8 ]      ( P2 )
 [ T9 ][T10 ][T11 ][T12 ]
   12 teclas               2 perillas (giro + click)
```

## Notas

- `F13`-`F24` no existen físicamente: por eso son ideales como combos "únicos".
- Las perillas vienen por defecto a **volumen/multimedia nativo** (funcionan
  aunque la app no esté corriendo). Las teclas vienen **sin asignar**, listas
  para tus scripts.
- El listener `keyboard` puede requerir ejecutar como administrador para
  suprimir las pulsaciones en todas las apps.
- El flasheo HID escribe en la interfaz de programación `MI_00` (usage page
  `0xFF00`); no afecta a la interfaz de escritura, así que el teclado sigue
  funcionando con normalidad.

## Créditos

Protocolo k884x portado desde [`ch57x-keyboard-tool`](https://github.com/kriomant/ch57x-keyboard-tool)
(MIT, de `kriomant`), enviado por HID nativo en lugar de libusb. Listener con
[`keyboard`](https://pypi.org/project/keyboard/). Licencia de este proyecto: [MIT](LICENSE).
