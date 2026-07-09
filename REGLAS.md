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

## Estructuración, Simplicidad y UX Predictivo
- **Simplicidad por Diseño:** Mantener la interfaz limpia, minimalista y libre de elementos innecesarios. Evitar la sobrecomplicación visual o del código.
- **Estructura Predictiva y Simetría:** El diseño debe ser intuitivo y predecible. Colocar los elementos de navegación, menús, acciones principales y botones en ubicaciones convencionales (patrones de diseño UX estándar). Buscar preferiblemente la simetría y el equilibrio visual en la distribución de bloques para transmitir orden y facilitar el escaneo visual de la pantalla.
- **Profundidad y Detalle en el Diseño:** Ir más allá de diseños planos o genéricos. Cuidar los detalles visuales de forma profunda: uso consistente de márgenes/paddings, tipografía con jerarquías claras, y aplicar sutiles efectos de profundidad (elevaciones, sombras suaves, transparencias o microinteracciones) que hagan que la interfaz se sienta de alta calidad y profesional.
## Directivas Obligatorias Multi-Proyecto (IA)
1. **Lectura y Registro Obligatorio en `FEEDBACK.md`**: Antes de iniciar cualquier tarea, leer `FEEDBACK.md`. Registrar automáticamente en `FEEDBACK.md` cualquier obstáculo técnico, error de compilación o sesión de depuración prolongada.
2. **Implementación Exhaustiva y Global**: Toda funcionalidad o cambio DEBE implementarse de forma global en toda la aplicación (sin hardcodeo ni componentes a medias).
3. **Reflexión Profunda y Verificación Multi-Paso**: Realizar auditoría interna de 2-3 pasadas (casos límite, temas claro/oscuro, idiomas) antes de presentar el trabajo.
4. **Planes de Implementación Proactivos**: Ante solicitudes complejas o ambigüedades, preparar plan estructurado y solicitar confirmación previa.


