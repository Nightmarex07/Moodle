<div align="center">

# 🎓 Moodle AI Assistant

**Asistente de IA con RAG para Moodle LMS**  
Chat contextual por curso, citas de fuentes y respuestas en tiempo real (streaming).

`FastAPI` · `PostgreSQL + pgvector` · `Google Gemini` · `Moodle Plugin (PHP/JS)` · `Docker`

</div>

---

## Tabla de contenidos

- [1. Qué es y cómo funciona](#1-qué-es-y-cómo-funciona)
- [2. Arquitectura y estructura](#2-arquitectura-y-estructura)
- [3. Requisitos previos](#3-requisitos-previos)
- [4. Paso a paso: puesta en marcha](#4-paso-a-paso-puesta-en-marcha)
  - [Paso 1 — Preparar el entorno](#paso-1--preparar-el-entorno)
  - [Paso 2 — Levantar los servicios con Docker](#paso-2--levantar-los-servicios-con-docker)
  - [Paso 3 — Acceder a Moodle](#paso-3--acceder-a-moodle)
  - [Paso 4 — Verificar e instalar el plugin](#paso-4--verificar-e-instalar-el-plugin)
  - [Paso 5 — Configurar el plugin en Moodle](#paso-5--configurar-el-plugin-en-moodle)
  - [Paso 6 — Crear un curso piloto e identificar su `course_id`](#paso-6--crear-un-curso-piloto-e-identificar-su-course_id)
  - [Paso 7 — Ingerir contenido (PDF/texto) para el RAG](#paso-7--ingerir-contenido-pdftexto-para-el-rag)
  - [Paso 8 — Probar el chat en Moodle](#paso-8--probar-el-chat-en-moodle)
- [5. APIs y pruebas técnicas (Swagger)](#5-apis-y-pruebas-técnicas-swagger)
- [6. Lecciones aprendidas y solución de problemas](#6-lecciones-aprendidas-y-solución-de-problemas)
- [7. Empaquetado y exportación](#7-empaquetado-y-exportación)
- [8. Documentación adicional](#8-documentación-adicional)

---

## 1. Qué es y cómo funciona

Este proyecto integra un **asistente conversacional** dentro de los cursos de Moodle. El asistente responde preguntas usando los materiales del curso mediante **RAG (Retrieval-Augmented Generation)**:

1. **Ingesta:** se extrae texto de documentos (PDF/texto o contenidos desde Moodle), se fragmenta y se generan *embeddings*.
2. **Almacenamiento:** los fragmentos se guardan en **PostgreSQL + pgvector** con metadatos (incluido `course_id`).
3. **Consulta:** al preguntar en el chat, se recuperan los fragmentos más relevantes **del mismo curso**.
4. **Generación:** el LLM (Google Gemini) genera la respuesta con ese contexto y la envía en **streaming (SSE)**, con citas/fuentes e historial.

**Capacidades clave:** aislamiento por curso, streaming en tiempo real, citas de fuentes, historial por usuario/curso, roles (estudiante/docente), guardrails básicos y proxy server-side en Moodle (la API key del backend no se expone al navegador).

---

## 2. Arquitectura y estructura

```text
┌──────────────────────── Moodle LMS ────────────────────────┐
│  Plugin local_ai_assistant (widget + proxy.php + config)   │
└──────────────────────────────┬─────────────────────────────┘
                               │ Sesión Moodle + sesskey
                               ▼
┌────────────────────── Backend (FastAPI) ───────────────────┐
│  Ingesta · Chunking · Embeddings · RAG · Chat/Streaming    │
└───────────────┬───────────────────────────────┬────────────┘
                │                               │
                ▼                               ▼
   PostgreSQL + pgvector                 LLM / Embeddings API
   (documentos, chunks, historial)       (Google Gemini)
```

```text
moodle-ai-assistant/
├─ backend/                  # FastAPI (API, RAG, chat, ingesta, embeddings)
│  ├─ app/api/routes.py
│  ├─ app/core/              # config.py, db.py
│  ├─ app/services/          # chat, rag, embeddings, guardrails, moodle...
│  ├─ db/init.sql
│  ├─ tests/
│  ├─ Dockerfile
│  └─ requirements.txt
├─ moodle-plugin/local/ai_assistant/  # Plugin Moodle (widget, proxy, settings)
├─ docs/                     # Sprints, despliegue, resumen, sustentación
├─ docker-compose.yml        # backend, db(pgvector), moodle, moodledb, redis
├─ .env.example
└─ README.md
```

**Servicios (Docker Compose):** `backend` (8000), `db` PostgreSQL+pgvector (5432), `moodle` (8080, opcional), `moodledb` MariaDB, `redis` (6379).

---

## 3. Requisitos previos

- **Docker** y **Docker Compose** instalados y en ejecución.
- **Clave de Google AI (Gemini API)** válida para embeddings y generación (`GOOGLE_API_KEY`).
- Navegador web para acceder a Moodle y Swagger.

> Nota: el entorno de desarrollo usado fue Windows/PowerShell; los comandos se indican en ese formato cuando aplica.

---

## 4. Paso a paso: puesta en marcha

### Paso 1 — Preparar el entorno

1. Ubícate en la raíz del proyecto:
   ```powershell
   cd C:\Users\Pc\moodle-ai-
   ```
2. Crea tu archivo de configuración:
   ```powershell
   copy .env.example .env
   ```
3. Edita `.env` y configura como mínimo:

   | Variable | Descripción | Ejemplo / nota |
   |---|---|---|
   | `API_KEY` | Clave interna Moodle ↔ Backend (header `X-API-Key`) | `change-me-local` (cámbiala en producción) |
   | `GOOGLE_API_KEY` | Clave de Google AI Studio (Gemini) | Debe ser válida y con acceso a los modelos usados |
   | `EMBEDDING_MODEL` | Modelo de embeddings | `models/gemini-embedding-001` (con salida 768 en este proyecto) |
   | `LLM_MODEL` | Modelo de chat/generación | p. ej. `models/gemini-3.8-flash` (según disponibilidad de tu clave) |
   | `MOODLE_BASE_URL` | URL de Moodle para ingesta vía WS (opcional) | `http://moodle:8080` (red Docker) o URL accesible |
   | `MOODLE_WS_TOKEN` | Token de Web Services de Moodle (opcional) | Para `POST /api/v1/moodle/ingest-course` |

   Variables del stack Moodle local (por defecto): `MOODLE_USERNAME=admin`, `MOODLE_PASSWORD=Admin123!`, `MOODLE_EMAIL=admin@example.com`, `MOODLE_SITE_URL=http://localhost:8080`.

> **Importante:** `GOOGLE_API_KEY` (Google) y `API_KEY` (backend interno) son distintas. No las mezcles.

### Paso 2 — Levantar los servicios con Docker

```powershell
docker compose up --build
# o en segundo plano:
# docker compose up -d --build
```

Verifica:
- **Moodle:** [http://localhost:8080](http://localhost:8080)
- **Backend / Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health:** [http://localhost:8000/health](http://localhost:8000/health) → `db: true`

Comandos útiles:
```powershell
docker compose ps
docker compose logs -f backend
docker compose logs -f moodle
docker compose down
# Reinicio limpio (borra datos/volúmenes):
# docker compose down -v
```

> La primera inicialización de Moodle puede tardar varios minutos.

### Paso 3 — Acceder a Moodle

- **URL:** [http://localhost:8080](http://localhost:8080)
- **Usuario:** `admin`
- **Contraseña:** `Admin123!` (según `.env`)
assistant
Si cambias credenciales en `.env` después de instalar, la imagen `erseco/alpine-moodle` puede reaplicarlas al reiniciar el contenedor:
```powershell
docker compose up -d --force-recreate moodle
```

### Paso 4 — Verificar e instalar el plugin

El plugin `local_ai_assistant` se monta en el contenedor de Moodle desde `moodle-plugin/local/ai_assistant`.

1. Si es la primera vez, ve a **Administración del sitio > Notificaciones**: [http://localhost:8080/admin/index.php](http://localhost:8080/admin/index.php) y completa la instalación/actualización.
2. Si dice “Nothing to display”, el plugin ya puede estar instalado. Accede directo a su configuración:
   - [http://localhost:8080/admin/settings.php?section=local_ai_assistant](http://localhost:8080/admin/settings.php?section=local_ai_assistant)
3. Si hiciste cambios y no se reflejan, purga cachés: [http://localhost:8080/admin/purgecaches.php](http://localhost:8080/admin/purgecaches.php)

### Paso 5 — Configurar el plugin en Moodle

En **Plugins locales > AI Assistant** configura y guarda:

| Campo | Valor (entorno Docker local) | Nota |
|---|---|---|
| **Enable assistant** | Activado | Muestra el widget en cursos |
| **Backend URL** | `http://backend:8000` | Desde Moodle en Docker se usa el nombre del servicio, **no** `localhost` |
| **Backend API key** | Valor de `API_KEY` en `.env` (ej. `change-me-local`) | Debe coincidir con el backend |

Después de guardar o cambiar archivos del plugin: **purga cachés** y recarga la página del curso (Ctrl+F5).

### Paso 6 — Crear un curso piloto e identificar su `course_id`

1. Crea un curso en Moodle y añade contenido si lo deseas.
2. Obtén el **ID del curso** desde la URL, por ejemplo:  
   `http://localhost:8080/course/view.php?id=2` → `course_id = 2`

El `course_id` usado en la ingesta debe ser el mismo que el del curso donde usarás el chat.

### Paso 7 — Ingerir contenido (PDF/texto) para el RAG

Sin contenido ingerido para ese curso, el chat no tendrá contexto. La forma más directa es usar **Swagger**.

1. Abre [http://localhost:8000/docs](http://localhost:8000/docs).
2. Usa **`POST /api/v1/ingest/pdf`** (o `/api/v1/ingest/text`) → *Try it out*.
3. Completa:
   - **`x-api-key`**: `change-me-local` (o tu `API_KEY`)
   - **`course_id`**: ID del curso (ej. `2`)
   - **`source_name`**: nombre descriptivo (ej. `Guía Unidad 1`)
   - **`file`**: selecciona el PDF
4. Ejecuta y verifica la respuesta: `status: "ok"` y **`chunks_stored > 0`**.

**Opcional (Moodle WS):** `POST /api/v1/moodle/ingest-course?course_id=<ID>` ingiere descripciones y archivos soportados (PDF/texto) si `MOODLE_BASE_URL` y `MOODLE_WS_TOKEN` están configurados correctamente.

### Paso 8 — Probar el chat en Moodle

1. Entra al curso (`http://localhost:8080/course/view.php?id=<course_id>`).
2. Haz clic en el **botón flotante** del asistente (esquina inferior derecha).
3. Escribe una pregunta sobre el material ingerido.
4. Deberías ver: respuesta en **streaming**, basada en el curso, con **fuentes/citas** e **historial** (persiste al recargar/reabrir).

---

## 5. APIs y pruebas técnicas (Swagger)

Base: `http://localhost:8000` — Docs: `/docs`

| Endpoint | Método | Descripción | Auth |
|---|---|---|---|
| `/health` | GET | Estado del servicio y BD | No |
| `/api/v1/ping` | GET | Ping autenticado | `X-API-Key` |
| `/api/v1/ingest/text` | POST | Ingesta de texto | `X-API-Key` |
| `/api/v1/ingest/pdf` | POST | Ingesta de PDF (`multipart/form-data`) | `X-API-Key` |
| `/api/v1/query` | POST | Búsqueda RAG por `course_id` | `X-API-Key` |
| `/api/v1/chat` | POST | Chat RAG (streaming SSE o JSON) | `X-API-Key` |
| `/api/v1/history` | GET | Historial por curso/usuario | `X-API-Key` |
| `/api/v1/moodle/ingest-course` | POST | Ingesta desde Moodle WS | `X-API-Key` |

Pruebas backend:
```powershell
cd backend
pytest -q
```

---

## 6. Lecciones aprendidas y solución de problemas

### Docker / Base de datos (PostgreSQL)
- **Error `role "moodle_ai" does not exist`:** el volumen de Postgres ya estaba inicializado con otras credenciales. Solución: `docker compose down`, eliminar el volumen `moodle-ai-assistant_postgres_data` y levantar de nuevo (o crear rol/BD manualmente).
- **Volumen en uso al eliminar:** detener contenedores (`docker compose down`), eliminar el contenedor que retiene el volumen (`docker rm -f <id>`) y luego `docker volume rm ...`.

### Moodle (contenedor `erseco/alpine-moodle`)
- **Conexión rechazada / instalación fallida:** revisar logs `docker compose logs -f moodle`. Se corrigió MariaDB para exigir UTF-8 (`utf8mb4`); si el volumen ya existía con otra configuración, fue necesario reiniciar `moodle_data` y `moodledb_data`.
- **Credenciales de admin:** esta imagen usa `MOODLE_USERNAME`, `MOODLE_PASSWORD`, `MOODLE_EMAIL` (no `MOODLE_ADMIN_*`). Tras cambiar `.env`, recrear el contenedor: `docker compose up -d --force-recreate moodle`.
- **Plugin no aparece en “Plugins locales”:** verificar en **Notificaciones** (`/admin/index.php`) para completar instalación. El plugin puede estar ya instalado aunque no se liste donde se espera; acceso directo: `/admin/settings.php?section=local_ai_assistant`. Purgar cachés.
- **Plugin no detectado por ubicación:** en Moodle 5.x con directorio `public/`, el plugin debe estar disponible en las rutas esperadas; se montó en `/var/www/html/local/ai_assistant` y `/var/www/html/public/local/ai_assistant`.
- **Error “Cannot require a CSS file after `<head>`…”:** no llamar `$PAGE->requires->css()` en hooks de footer; cargar CSS en `before_standard_head_html_generation`.
- **Widget no abre al hacer clic:** faltaban archivos AMD compilados. Se añadieron `amd/build/chat_widget.js` y `.min.js`. Después, purgar cachés de Moodle y recargar (Ctrl+F5).
- **Configuración del plugin:** en red Docker, **Backend URL** debe ser `http://backend:8000` (no `localhost`). Si el formulario rechaza el valor, usar un tipo de parámetro permisivo y/o configurar por CLI (`php admin/cli/cfg.php --component=local_ai_assistant ...`).

### Proxy Moodle ↔ Backend
- **`500` en `proxy.php?action=history/chat`:** puede deberse a Backend URL/API key vacíos o mal configurados, o errores de conexión.
- **`URL rejected: Malformed input to a URL function`:** causado por espacios en la URL guardada; se corrigió aplicando `trim()` a `backendurl`/`apikey` y reconfigurando valores.
- **Streaming en blanco o diferido:** ajustar manejo de buffering/flush y cabeceras SSE en `proxy.php` (`X-Accel-Buffering: no`, limpieza de buffers, `flush`) para permitir respuesta en tiempo real.

### Google AI / Gemini (clave, modelos y RAG)
- **`x-api-key` (Swagger/Moodle→Backend) ≠ `GOOGLE_API_KEY`:** la primera es `API_KEY` interna del backend; la segunda es la clave de Google AI usada por el servidor.
- **Clave de Google inválida o no reconocida:** se requiere una clave válida de Google AI Studio con acceso a la API/modelos necesarios. Una clave válida puede listar modelos correctamente; si falla, revisar acceso/proyecto/modelos disponibles.
- **Errores de embeddings/modelo (`404 ... not found for embedContent`):** el nombre del modelo debe existir para la clave. Se identificaron modelos de embedding disponibles (ej. `models/gemini-embedding-001`) y se configuró `output_dimensionality=768` para coincidir con `VECTOR(768)` en la BD.
- **Chat sin respuesta (respuesta vacía):** el modelo de generación configurado puede no estar disponible para la clave. Se debe usar un modelo válido (ej. `models/gemini-3.8-flash`, según disponibilidad) y reiniciar el backend.
- **`Internal Server Error` al ingerir:** revisar `docker compose logs -f backend`. Causas comunes: clave/modelo de embeddings inválido, falta de acceso o configuración incorrecta.
- **Tras cambiar `.env`:** reiniciar/reconstruir backend (`docker compose up -d --build backend`).

### Base de datos de la aplicación (chat/historial)
- **Error SQL por parámetro `NULL` ambiguo:** consultas con `:user_id` comparado en formas que confunden al driver se corrigieron usando `CAST(:user_id AS TEXT)` en las condiciones `IS NULL`/comparación.

### Verificación y depuración rápida
```powershell
# Estado y logs
docker compose ps
docker compose logs --tail 100 backend
docker compose logs --tail 100 moodle

# Prueba backend desde host
curl http://localhost:8000/health

# Revisar configuración del plugin dentro de Moodle (contenedor)
docker compose exec moodle php admin/cli/cfg.php --component=local_ai_assistant
```
- En el navegador: **F12 > Network** (respuesta de `proxy.php?action=chat|history`) y **Console** para errores JS.
- Si la respuesta no aparece en tiempo real, confirmar que el backend genera streaming y que no hay buffering en proxy/cliente.

---

## 7. Empaquetado y exportación

### Empaquetar el plugin Moodle (ZIP)
```powershell
cd C:\Users\Pc\moodle-ai-assistant
Compress-Archive -Path .\moodle-plugin\local\ai_assistant -DestinationPath .\local_ai_assistant.zip -Force
```

### Exportar el proyecto completo
- **Opción recomendada (compartir sin secretos):** crear un ZIP excluyendo `.env`, `__pycache__`, etc., e incluir `.env.example`.
- **Opción rápida:** comprimir toda la carpeta en ZIP (ten en cuenta que incluirá `.env` y credenciales locales si existe).

En otro equipo: descomprimir, crear `.env` desde `.env.example`, configurar claves y ejecutar `docker compose up --build`.

---

## 8. Documentación adicional

- [`docs/SUSTENTACION.md`](docs/SUSTENTACION.md) — guion de demo y checklist
- [`docs/RESUMEN_PROYECTO.md`](docs/RESUMEN_PROYECTO.md) — resumen ejecutivo
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — despliegue
- [`docs/SPRINT1.md`](docs/SPRINT1.md) a [`docs/SPRINT4.md`](docs/SPRINT4.md) — evolución por sprints
- [`docs/NEXT.md`](docs/NEXT.md) — mejoras y siguientes pasos
- [`moodle-plugin/local/ai_assistant/README.md`](moodle-plugin/local/ai_assistant/README.md) — notas del plugin
- [`LICENSE`](LICENSE)

---
<div align="center"><sub>Moodle AI Assistant — MVP con RAG, streaming y integración Moodle</sub></div>
