# Asistente IA para Moodle LMS
> Resumen ejecutivo del proyecto, funcionamiento y borrador de comunicación.

---

## 1. Ubicación del proyecto

| Elemento | Detalle |
|---|---|
| **Raíz del proyecto** | `C:\Users\Pc\moodle-ai-assistant` |
| **Backend (FastAPI)** | `backend/` |
| **Plugin Moodle** | `moodle-plugin/local/ai_assistant/` |
| **Orquestación Docker** | `docker-compose.yml` |
| **Configuración** | `.env` / `.env.example` |
| **Documentación** | `docs/` (`SPRINT1-4.md`, `DEPLOYMENT.md`, `NEXT.md`) |

---

## 2. ¿De qué trata el proyecto?

El proyecto integra un **asistente conversacional de IA dentro de Moodle LMS** para ayudar a estudiantes y docentes a consultar el material de cada curso de forma rápida, contextualizada y con trazabilidad.

**Objetivos clave**
- Responder con base en los contenidos reales del curso (PDFs, guías, recursos).
- Aislar el contexto por asignatura (`course_id`) para evitar mezclar información entre cursos.
- Citar fuentes cuando la respuesta se apoya en material recuperado.
- Ofrecer una experiencia fluida dentro del aula virtual (chat en tiempo real).

---

## 3. ¿Cómo funciona?

La solución usa una arquitectura desacoplada con enfoque **RAG (Retrieval-Augmented Generation)**:

| Capa | Componente | Función principal |
|---|---|---|
| **LMS** | Plugin `local_ai_assistant` (Moodle) | Widget de chat en el curso y proxy server-side seguro hacia el backend. |
| **Backend** | FastAPI (Python) | Orquestación del chat, ingesta, recuperación y generación de respuestas. |
| **Conocimiento** | PostgreSQL + `pgvector` | Almacenamiento de fragmentos y embeddings filtrados por curso. |
| **IA** | Modelo LLM vía API (Google Gemini) | Generación de respuestas contextualizadas (streaming). |

**Flujo resumido**
1. **Ingesta:** se extrae texto de los materiales (PDF/texto, contenidos de Moodle), se fragmenta (~500 tokens) y se generan embeddings con metadatos (`course_id`, `section_id`, fuente).
2. **Consulta:** el usuario pregunta desde el widget; el backend recupera los fragmentos más relevantes del curso.
3. **Generación:** el LLM responde usando ese contexto, en *streaming* (SSE), con citas/referencias a las fuentes.
4. **Controles:** historial por usuario/curso, roles (tutor socrático para estudiantes / analítico para docentes), guardrails básicos (alcance al material, cuota y redacción de PII).

---

## 4. Estado actual (resumen)

- ✅ **Sprint 1:** infraestructura base, FastAPI (health/ping), Docker, widget/plugin Moodle.
- ✅ **Sprint 2:** ingesta de texto/PDF, chunking, embeddings y consulta RAG filtrada por curso.
- ✅ **Sprint 3:** chat E2E con streaming, citas, historial persistente y roles.
- ✅ **Sprint 4:** guardrails iniciales, proxy seguro en Moodle, documentación y empaquetado.
- ➕ **Mejoras:** ingesta de archivos desde Moodle WS, Redis en infraestructura y pruebas básicas (`pytest`).

> Detalle técnico: ver `docs/DEPLOYMENT.md`, `docs/SPRINT1-4.md` y `docs/NEXT.md`.

---

## 5. Borrador de correo para compañero

**Asunto:** Presentación y resumen del proyecto: Asistente IA para Moodle LMS

Hola [Nombre del compañero],

Espero que estés muy bien. Mi nombre es **[Tu nombre]** y me gustaría presentarte el proyecto en el que he estado trabajando: un **Asistente de Inteligencia Artificial para Moodle LMS**.

### ¿De qué trata el proyecto?
El objetivo es integrar un asistente conversacional dentro de los cursos de Moodle que ayude a estudiantes y docentes a consultar el material del curso de forma rápida y contextualizada. El asistente responde con base en los contenidos de cada asignatura (por ejemplo, PDFs, guías y recursos del curso), evitando mezclar información entre cursos distintos y citando las fuentes cuando es posible.

### ¿Cómo funciona?
La solución utiliza una arquitectura desacoplada con enfoque **RAG (Retrieval-Augmented Generation)**:

1. **Plugin en Moodle (`local_ai_assistant`)**: incorpora un widget de chat en las páginas del curso. La comunicación con el backend se realiza de forma segura desde el servidor de Moodle (proxy), sin exponer credenciales en el navegador.
2. **Backend en FastAPI (Python)**: recibe las consultas, gestiona la lógica del chat y se conecta al modelo de lenguaje (LLM) mediante API.
3. **Ingesta y base de conocimiento**: los materiales del curso se procesan (extracción de texto, fragmentación y generación de *embeddings*) y se almacenan en una base vectorial (**PostgreSQL + pgvector**), asociando cada fragmento a su curso.
4. **Consulta y respuesta**: cuando un usuario hace una pregunta, el sistema recupera los fragmentos más relevantes del curso, construye el contexto y el LLM genera una respuesta en tiempo real (*streaming*), con citas/referencias a las fuentes.
5. **Controles adicionales**: incluye historial de conversación por usuario/curso, manejo de roles (estudiante/docente) y guardrails básicos (control de alcance al material del curso, límites de uso y redacción básica de datos sensibles).

Actualmente el proyecto cuenta con el backend contenerizado (Docker), el plugin de Moodle, endpoints para ingesta/consulta/chat, documentación técnica y una guía de despliegue.

Si te parece, podemos coordinar un espacio para mostrarte una demo y revisar posibles mejoras o siguientes pasos.

Quedo atento/a a tus comentarios.

Saludos cordiales,  
**[Tu nombre]**  
[Tu cargo/rol, opcional]  
[Tu correo / contacto, opcional]

---
*Documento generado como resumen de referencia del proyecto.*
