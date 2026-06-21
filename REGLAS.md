# Reglas — hotkeyconfig

Hereda las reglas generales de `C:\proyectos\Reglas_de_los_proyectos.md` y añade
las propias del proyecto.

## Generales (heredadas)
- **Nunca** poner `Co-Authored-By` en los commits/push.
- Cada cambio lleva una explicación clara y una estructuración óptima.
- **Preguntar siempre antes de hacer push** a GitHub.
- Usar todas las herramientas que hagan falta, con responsabilidad.
- Buscar en la web la mejor herramienta para cada tarea (no reinventar).
- **Nunca** filtrar API keys ni contenido sensible.
- Cuantificar el coste de cada idea: validar el producto real → MVP funcional →
  feedback → escalar.

## Específicas del proyecto
- **Ciberseguridad primero**: dependencias legítimas, verificadas y auditadas
  (`pip-audit` + `cargo audit`), sin puertas traseras. Ver [SECURITY.md](SECURITY.md).
- **Preguntar antes de grabar el teclado** (`flash`): es una escritura sobre el
  hardware del usuario.
- El listener no registra pulsaciones normales ni hace red. Mantenerlo así.
- `profile.yaml` real nunca se versiona; solo `profile.example.yaml`.
- Dependencias mínimas y fijadas en `pyproject.toml`. Antes de añadir una nueva,
  justificar por qué no basta con lo que ya hay.
- Mantener el alcance **simple** (es la petición original): unir flasher +
  listener, no construir un IDE de macros.
