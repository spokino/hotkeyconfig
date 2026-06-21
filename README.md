# hotkeyconfig

App **open source** y sencilla para convertir un macropad chino barato (los de
AliExpress basados en el chip **ch57x**, p. ej. `1189:8842` — 12 teclas + 2
perillas + 3 capas) en un panel de atajos donde **cada tecla ejecuta el script
o la acción que tú quieras**.

> Programa el teclado **sin el software propietario** que viene en un Google
> Drive, desde un único archivo de configuración, y con un listener que no es un
> keylogger (ver [SECURITY.md](SECURITY.md)).

## ¿Por qué existe?

Estos macropads no exponen un identificador único por tecla: emiten pulsaciones
HID estándar. Para hacer cada tecla **única** hay que asignarle una combinación
que ningún teclado físico produce. `hotkeyconfig` usa las teclas fantasma
`F13`–`F24` con familias de modificadores distintas por capa, generando **54
combos únicos sin colisión** (12 teclas × 3 capas + 2 perillas × 3 acciones × 3
capas). Luego un proceso en segundo plano escucha esos combos y ejecuta tu acción.

Las dos mitades difíciles se **reutilizan**, no se reinventan:

| Mitad | Herramienta | Rol |
|-------|-------------|-----|
| Grabar combos en el teclado | [`kriomant/ch57x-keyboard-tool`](https://github.com/kriomant/ch57x-keyboard-tool) | flasher USB |
| Escuchar combos y actuar | librería [`keyboard`](https://pypi.org/project/keyboard/) | listener global |

`hotkeyconfig` es el **pegamento**: genera los combos, programa el hardware y
gestiona las acciones desde `profile.yaml`.

## Instalación

```bash
# 1) Flasher del teclado (Rust)
cargo install ch57x-keyboard-tool --locked

# 2) La app (Python 3.11+)
python -m venv .venv
.venv\Scripts\pip install -e ".[windows]"
```

## Uso en 4 pasos

```bash
hotkeyconfig detect                 # comprueba herramienta + teclado conectado
hotkeyconfig generate               # crea config/profile.yaml con 54 combos únicos
#   …edita profile.yaml y asigna acciones a tus teclas…
hotkeyconfig flash                  # graba los combos en el teclado
hotkeyconfig run                    # escucha y ejecuta (icono en la bandeja)
```

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
| `unassigned` | Sin asignar | — |

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

- `F13`–`F24` no existen físicamente: por eso son ideales como combos "únicos".
- Las perillas vienen por defecto a **volumen/multimedia nativo** (funcionan
  aunque la app no esté corriendo). Las teclas vienen **sin asignar**, listas
  para tus scripts.
- El listener `keyboard` puede requerir ejecutar como administrador para
  suprimir las pulsaciones en todas las apps.

## Créditos

Construido sobre [`ch57x-keyboard-tool`](https://github.com/kriomant/ch57x-keyboard-tool)
(MIT, de `kriomant`). Licencia de este proyecto: [MIT](LICENSE).
