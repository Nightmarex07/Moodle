# `local_ai_assistant` — Plugin Moodle

Plugin local de Moodle que integra un **widget de chat IA** en las páginas de curso y se comunica con el backend mediante un **proxy server-side** (`proxy.php`).

## Instalación

1. Copiar esta carpeta a `<moodle>/local/ai_assistant`.
2. Ir a **Administración del sitio > Notificaciones** para completar la instalación/actualización.
3. Configurar en **Administración del sitio > Plugins > Plugins locales > AI Assistant**:
   - **Backend URL** (accesible desde el servidor Moodle)
   - **Backend API key** (coincide con `API_KEY` del backend)

## Funcionamiento

- El widget se muestra en el contexto de curso (según permisos y configuración).
- `proxy.php` valida sesión de Moodle, `sesskey` y acceso al curso antes de reenviar solicitudes al backend.
- Soporta carga de historial y chat en streaming (SSE) con visualización de fuentes.

## Notas

- Purga cachés de Moodle tras actualizar JS/plantillas.
- Requiere Moodle 4.4+ (hook de salida utilizado en el scaffold).
- Consulta la documentación general en [`../../docs/DEPLOYMENT.md`](../../docs/DEPLOYMENT.md).
