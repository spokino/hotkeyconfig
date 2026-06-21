# Seguridad

`hotkeyconfig` instala dependencias y usa un **hook global de teclado**: una zona
sensible. Estos son los compromisos del proyecto.

## El listener NO es un keylogger

- Solo reacciona a los **combos `F13`–`F24` configurados** en tu `profile.yaml`.
- **No** registra, almacena ni transmite tus pulsaciones normales.
- **No** hace ninguna llamada de red. No hay telemetría.
- Todo el código es open source y auditable (`hotkeyconfig/runtime.py`,
  `actions.py`).

## Dependencias legítimas y verificadas

- **`ch57x-keyboard-tool`**: repo público conocido (MIT, autor `kriomant`).
  Se instala desde **crates.io** con `--locked` (fija el árbol de dependencias
  transitivas para builds reproducibles). Conviene revisar el código antes de
  compilar y fijar la versión.
- **Dependencias Python**: mínimas y solo de **PyPI** oficial
  (`PyYAML`, `keyboard`, `pystray`, `Pillow`, opcional `pywin32`).
- **Auditoría**: `pip-audit` (Python) y `cargo audit` (árbol de ch57x) deben
  pasar sin vulnerabilidades conocidas antes de publicar.

```bash
pip-audit                 # deps Python
cargo audit               # deps de ch57x-keyboard-tool
```

### Estado de auditoría (2026-06-21)

- **`pip-audit`**: sin vulnerabilidades conocidas en las dependencias Python.
- **`cargo audit`** sobre el árbol de `ch57x-keyboard-tool` 1.7.0 (105 crates):
  3 avisos, **todos en dependencias transitivas de la herramienta**, ninguno en
  código de este proyecto:
  - `RUSTSEC-2026-0009` (`time`, medium 6.8): DoS por agotamiento de pila al
    **parsear cadenas de tiempo no confiables**. No aplica a nuestro uso: solo le
    pasamos YAML generado por nosotros y la herramienta corre bajo demanda en local.
  - `RUSTSEC-2024-0370` (`proc-macro-error`): crate de build sin mantenimiento.
  - `RUSTSEC-2023-0075` (`unsafe-libyaml`): escritura desalineada solo en
    plataformas de **32/16 bits** (no afecta a Windows x64).
- Conclusión: `ch57x-keyboard-tool` es legítimo (repo MIT conocido) y sin puertas
  traseras; los avisos son de bajo riesgo en su árbol upstream. Se recomienda
  reportarlos/actualizar upstream cuando publiquen una versión con `time>=0.3.47`.

## Sin secretos en el repositorio

- Nunca se versionan API keys ni rutas privadas.
- Tu `config/profile.yaml` real está en `.gitignore`; solo se publica
  `config/profile.example.yaml`.

## Ejecución de scripts del usuario

Las acciones `run` ejecutan **lo que tú defines** en tu propio `profile.yaml`,
en local y bajo tu control. La app **no** descarga ni evalúa código de fuentes
externas.

## Reportar una vulnerabilidad

Abre un *issue* privado o contacta al mantenedor. No publiques detalles
explotables hasta que exista un parche.
