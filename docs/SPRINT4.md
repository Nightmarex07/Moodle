# Sprint 4 — Guardrails, Pruebas y Despliegue

## Implementado

- **Guardrails (backend)** (`app/services/guardrails.py`, integrado en `chat.py`):
  - **Límite de cuota** en memoria por usuario/curso (ventana horaria) para reducir abuso/sobrecarga.
  - **Redacción básica de PII** en entrada (p. ej. correos y teléfonos) antes de persistir/procesar.
  - **Control de alcance (heurístico)**: si no hay contexto recuperado relevante para el curso, se responde con el mensaje de “información no encontrada en el material del curso” en lugar de generar fuera de contexto.
  - El prompt del sistema refuerza: responder solo con contexto del curso, citar fuentes y manejar vacíos de información.

- **Hardening de seguridad (Moodle ↔ backend)**:
  - Añadido `local/ai_assistant/proxy.php` (server-side) que valida sesión (`require_login`, `sesskey`, capacidad de acceso al curso), lee `backendurl/apikey` desde configuración del plugin y reenvía al backend sin exponer la API key al navegador.
  - El widget usa el proxy para historial y chat streaming.

- **Documentación y empaquetado**:
  - Guía de despliegue: `docs/DEPLOYMENT.md`.
  - Estructura lista para generar ZIP instalable del plugin (`local/ai_assistant`).

## Pruebas recomendadas (checklist)

- **Funcionales**: ingesta PDF/texto por curso, consulta RAG aislada por `course_id`, chat streaming con citas, historial por usuario/curso, roles estudiante/docente.
- **Seguridad/aislamiento**: usuario del Curso A no recibe contexto del Curso B; sin acceso al curso no puede usar proxy; `sesskey` inválido rechazado; API key no visible en HTML/JS del cliente.
- **Guardrails**: preguntas fuera de material → respuesta de vacío controlado; PII en entrada redactada en mensajes almacenados; límite de cuota aplicado.
- **Carga/latencia**: pruebas concurrentes de `/api/v1/chat` y streaming (p. ej. k6/Locust), medir TTFB y tiempo total; validar comportamiento bajo múltiples usuarios y cursos.
- **Aceptación piloto**: docentes y estudiantes validan relevancia, claridad de citas y manejo de preguntas no cubiertas.

## Pendientes / mejoras sugeridas

- Guardrails más robustos (clasificador de intención/fuera de ámbito, detección de PII ampliada, moderación de contenido).
- Rate limiting distribuido (Redis) y caching semántico de respuestas frecuentes.
- Proxy con soporte robusto de errores/timeout y observabilidad (logs, métricas, trazas).
- Descarga real de archivos del curso desde Moodle WS y mejoras de citación (página/sección exacta cuando aplique).
- Pruebas automatizadas (unitarias/integración) y pipeline CI/CD.
