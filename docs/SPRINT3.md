# Sprint 3 — Integración End-to-End y Streaming

## Implementado

- **Chat RAG con streaming SSE**: `POST /api/v1/chat` recupera contexto vectorial por `course_id`, construye prompt con rol y genera respuesta con Gemini en streaming (`text/event-stream`, eventos `meta`, `token`, `error`, `done`).
- **Gestión de roles en prompt**: modo tutor socrático para `student` y analítico para `teacher`.
- **Citas/fuentes**: el backend devuelve fuentes recuperadas en `meta.citations` y el prompt exige citar fuentes (`[Fuente: ...]`); el widget muestra fuentes bajo la respuesta.
- **Historial persistente**: tablas `conversations` y `messages` (por curso/usuario), endpoint `GET /api/v1/history` y carga de historial al abrir el widget.
- **Plugin Moodle**: el widget envía `course_id`, `user_id` y `user_role` (docente si tiene `moodle/course:manageactivities`), consume SSE vía `fetch` streaming y renderiza la respuesta incrementalmente.

## Notas

- Para BDs ya inicializadas, el backend crea las tablas de chat bajo demanda (`ensure_chat_schema`) al usar endpoints de chat/historial.
- El renderizado Markdown en el widget es básico (negritas, cursivas, saltos de línea) y las citas se muestran como lista de fuentes.
- **Seguridad (pendiente Sprint 4):** el scaffold aún expone `X-API-Key` al cliente y confía en parámetros enviados por el navegador; en producción se debe mediar por endpoints/servicios del servidor Moodle con sesión/autorización real y no exponer secretos.
- Si el modelo configurado en `LLM_MODEL` no está disponible para tu clave/proyecto de Google, ajusta el valor en `.env` (p. ej. un modelo Gemini vigente para tu cuenta).
