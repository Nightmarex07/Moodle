# Sprint 1 — Infraestructura Base y Comunicación

## Objetivo
Tener un widget de chat montado en Moodle capaz de comunicarse con un backend externo mediante un ping autenticado.

## Entregables en este scaffold

- **Backend (FastAPI)**: `GET /health`, `GET /api/v1/ping` (header `X-API-Key`).
- **Docker Compose**: servicios `backend` y `db` (PostgreSQL + `pgvector`).
- **Plugin Moodle (`local_ai_assistant`)**: configuración admin, inyección de widget en contexto de curso, UI flotante y prueba de ping al abrir.

## Cómo probar

1. Copiar `.env.example` a `.env` y ajustar `API_KEY`.
2. Ejecutar `docker compose up --build`.
3. Verificar `http://localhost:8000/health` y `http://localhost:8000/docs`.
4. Instalar `moodle-plugin/local/ai_assistant` en una instancia Moodle 4.4+ y configurar URL/API key.
5. Abrir un curso y comprobar que el widget aparece y reporta conexión al backend.

## Pendientes próximos (Sprint 2+)

- Ingesta de contenidos del curso vía Moodle Web Services.
- Chunking, embeddings y búsqueda vectorial filtrada por `course_id`.
- Endpoint de chat/RAG y streaming SSE.
- Endurecer seguridad (no exponer API key al cliente; usar proxy/tokens por sesión).
