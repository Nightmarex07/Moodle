# Sprint 2 — Pipeline RAG e Ingesta de Documentos

## Implementado en este scaffold

- **Extracción de texto PDF** (`pypdf`) desde uploads.
- **Chunking semántico aproximado por tokens** (objetivo ~500 tokens, solapamiento configurable) usando `tiktoken`.
- **Embeddings con Google** (`google-generativeai`, modelo configurable vía `EMBEDDING_MODEL`).
- **Almacenamiento vectorial en PostgreSQL + pgvector** (`documents`, `document_chunks`) con metadatos y filtrado estricto por `course_id`.
- **Endpoints API** (autenticados con `X-API-Key`):
  - `POST /api/v1/ingest/text` — ingesta de texto con `course_id`, `section_id`, `source_name`.
  - `POST /api/v1/ingest/pdf` — ingesta de PDF (`multipart/form-data`: `course_id`, `source_name`, opcional `section_id`, `file`).
  - `POST /api/v1/query` — consulta vectorial filtrada por `course_id` (`query`, `top_k`).
  - `POST /api/v1/moodle/ingest-course?course_id=...` — ingesta básica desde Moodle Web Services (`core_course_get_contents`: resúmenes/descripciones). La descarga de archivos adjuntos requiere ampliar la integración con APIs de archivos de Moodle.

## Configuración requerida (`.env`)

- `GOOGLE_API_KEY` — clave de API de Google (Gemini/embeddings).
- `EMBEDDING_MODEL` — por defecto `models/text-embedding-004`.
- `DATABASE_URL` — conexión a PostgreSQL con `pgvector`.
- `MOODLE_BASE_URL` y `MOODLE_WS_TOKEN` — necesarios para ingesta desde Moodle.

## Pruebas rápidas (Swagger)

1. Levantar servicios: `docker compose up --build`.
2. Abrir `http://localhost:8000/docs`.
3. Autorizar requests con header `X-API-Key`.
4. Ingerir un PDF o texto para un `course_id`.
5. Consultar con `/api/v1/query` y verificar que los resultados pertenecen al mismo curso.

## Notas

- La dimensión del vector en `document_chunks.embedding` está definida como `VECTOR(768)` en `db/init.sql` (compatible con embeddings de Google comunes). Si cambias de modelo con otra dimensión, ajusta el esquema.
- `tiktoken`/descarga de codificaciones puede requerir acceso a red en el primer uso; hay fallback de chunking por caracteres.
- El crawler de Moodle en este sprint es un punto de partida (metadatos/descripciones); para PDFs/archivos del curso se debe resolver y descargar contenido vía endpoints de ficheros de Moodle con permisos adecuados.
