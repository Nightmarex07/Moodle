# Guía de Despliegue (MVP)

## Componentes

- **Backend IA**: FastAPI + RAG (PostgreSQL/pgvector, embeddings/LLM Google Gemini).
- **Plugin Moodle**: `local_ai_assistant` (widget de chat + proxy server-side hacia el backend).

## Requisitos

- Docker y Docker Compose (recomendado para despliegue del backend).
- Moodle 4.4+ con permisos de administración para instalar plugins locales.
- Clave/API de Google configurada en el backend (`GOOGLE_API_KEY`).
- Conectividad de red desde el servidor Moodle hacia el backend.

## 1) Backend

1. Configurar variables de entorno:
   - Copiar `.env.example` a `.env`.
   - Definir `API_KEY` (secreto compartido Moodle↔backend), `GOOGLE_API_KEY`, `DATABASE_URL` (o usar el servicio `db` del compose), y parámetros de Moodle si se usará ingesta WS.
2. Levantar servicios:
   ```bash
   docker compose up -d --build
   ```
3. Verificar:
   - `GET /health` responde `status=ok` y `db=true`.
   - Ingerir contenido de prueba (texto/PDF) y validar `POST /api/v1/query` / `POST /api/v1/chat`.

> Nota: si actualizas el esquema y la BD ya existía, aplica cambios de tablas o recrea el volumen de datos según corresponda.

## 2) Plugin Moodle

1. Empaquetar el plugin (contenido de la carpeta `local/ai_assistant` dentro de un ZIP con esa ruta) o copiarlo al servidor:
   - Ruta destino: `<moodle>/local/ai_assistant`
2. Instalar/actualizar desde **Administración del sitio > Notificaciones** (o mediante el instalador de plugins).
3. Configurar en **Administración del sitio > Plugins > Plugins locales > AI Assistant**:
   - **Backend URL**: URL accesible desde el servidor Moodle (ej. `http://backend:8000` en red Docker interna o URL pública/privada).
   - **Backend API key**: debe coincidir con `API_KEY` del backend.
4. Purgar cachés de Moodle y probar en una página de curso.

## 3) Seguridad y operación

- El navegador se comunica con `local/ai_assistant/proxy.php` (sesión Moodle + `sesskey` + capacidad de curso); la API key del backend se mantiene en configuración del servidor.
- Restringir CORS/orígenes del backend y exponerlo solo en redes confiables.
- Configurar HTTPS, secretos seguros, rotación de claves y límites de cuota adecuados.
- Realizar ingesta de materiales por curso antes de habilitar el uso con estudiantes.

## 4) Empaquetado del plugin (ZIP)

Ejemplo en PowerShell (desde la raíz del proyecto):
```powershell
Compress-Archive -Path .\moodle-plugin\local\ai_assistant -DestinationPath .\local_ai_assistant.zip -Force
```
El ZIP debe contener la carpeta `ai_assistant` (o `local/ai_assistant` según el método de instalación) para que Moodle reconozca el componente `local_ai_assistant`.
