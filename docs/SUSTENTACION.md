# Guía de Sustentación y Demo — Moodle AI Assistant

## 1. Objetivo de la demo
Demostrar un asistente de IA integrado en Moodle que responde preguntas sobre el material de un curso usando **RAG (Retrieval-Augmented Generation)**, con respuestas en tiempo real, contexto por curso e historial.

---

## 2. Preparación previa (checklist)

### Infraestructura
- [ ] Servicios en ejecución: `docker compose up -d --build` (en `C:\Users\Pc\moodle-ai-assistant`)
- [ ] Backend operativo: [http://localhost:8000/health](http://localhost:8000/health) → `status: ok`, `db: true`
- [ ] Moodle operativo: [http://localhost:8080](http://localhost:8080)

### Configuración
- [ ] `.env` con claves válidas (`GOOGLE_API_KEY`, `API_KEY`) y modelos disponibles (`EMBEDDING_MODEL`, `LLM_MODEL`)
- [ ] Plugin configurado en Moodle ([AI Assistant](http://localhost:8000/admin/settings.php?section=local_ai_assistant) en `localhost:8080`):
  - **Enable assistant:** activado
  - **Backend URL:** `http://backend:8000`
  - **Backend API key:** igual a `API_KEY` del `.env`

### Datos de prueba
- [ ] Curso piloto creado y con `course_id` identificado (ej. `id=2`)
- [ ] Material ingerido para ese curso (`POST /api/v1/ingest/pdf` o `/ingest/text`, `chunks_stored > 0`)
- [ ] Cachés de Moodle purgadas si hubo cambios recientes

---

## 3. Guion de demo (5–8 minutos)

### A. Contexto (1 min)
- **Problema:** consultar material del curso en Moodle puede ser lento y disperso.
- **Solución:** asistente IA dentro del curso que responde con base en los recursos de la asignatura (RAG), con citas y streaming.

### B. Arquitectura (1–2 min)
- **Moodle (plugin `local_ai_assistant`)**: widget + proxy seguro (sesión/sesskey, sin exponer API key al navegador).
- **Backend FastAPI**: ingesta, chunking, embeddings, búsqueda vectorial y generación con LLM.
- **PostgreSQL + pgvector**: almacenamiento de chunks/embeddings e historial, filtrado por `course_id`.
- **Flujo:** pregunta → recuperación de contexto del curso → respuesta en streaming con fuentes.

### C. Demostración en vivo (3–4 min)
1. **Mostrar el curso en Moodle** (`http://localhost:8080/course/view.php?id=<course_id>`).
2. **Abrir el widget** (botón flotante) y enviar una pregunta sobre el PDF/material ingerido.
3. **Resaltar:**
   - Respuesta en tiempo real (streaming)
   - Respuesta basada en el contenido del curso
   - Citas/fuentes mostradas en el chat
   - Historial persistente (recargar y reabrir el chat)
4. **(Opcional, Swagger)** mostrar evidencia técnica: `GET /health`, ingesta realizada (`chunks_stored`) o `POST /api/v1/query` para el `course_id`.

### D. Cierre (1 min)
- **Logros (MVP/Sprints):** integración Moodle↔backend, pipeline RAG, chat E2E con streaming, guardrails básicos y documentación/despliegue.
- **Próximos pasos:** ingesta automática más amplia de recursos Moodle, caché/rate limiting distribuido (Redis), observabilidad, pruebas automatizadas y hardening para producción.

---

## 4. Preguntas frecuentes (respuestas breves)
- **¿De dónde saca la información?** De los materiales ingeridos del curso; la búsqueda se filtra por `course_id`.
- **¿Puede inventar respuestas?** El sistema instruye responder con el contexto disponible y citar fuentes; si no hay información, indica que no se encuentra en el material.
- **¿Es seguro?** El navegador usa un proxy en Moodle con sesión/sesskey; la API key del backend no se expone al cliente (mejorable para producción).
- **¿Funciona en tiempo real?** Sí, la respuesta se transmite por SSE (streaming).

---

## 5. Entregables
- Código del proyecto: `C:\Users\Pc\moodle-ai-assistant`
- Documentación: `README.md`, `docs/DEPLOYMENT.md`, `docs/SPRINT1-4.md`, `docs/NEXT.md`, `docs/RESUMEN_PROYECTO.md`
- Plugin empaquetado: `local_ai_assistant.zip` (en la raíz del proyecto, si fue generado)

## 6. Comandos útiles
```powershell
# Levantar entorno
cd C:\Users\Pc\moodle-ai-assistant
docker compose up -d --build

# Estado y logs
docker compose ps
docker compose logs -f backend
docker compose logs -f moodle

# Empaquetar plugin
Compress-Archive -Path .\moodle-plugin\local\ai_assistant -DestinationPath .\local_ai_assistant.zip -Force
```