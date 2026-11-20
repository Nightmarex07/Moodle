# Mejoras adicionales (post-Sprint 4)

## Implementado

- **Ingesta Moodle más completa**: `POST /api/v1/moodle/ingest-course` ahora recorre `contents` de los módulos, descarga archivos vía `fileurl` con token y extrae/ingesta contenido soportado (PDF y archivos de texto como `.txt`, `.md`, `.html`), además de resúmenes/descripciones.
- **Infraestructura**: servicio `redis` agregado en `docker-compose.yml` como base para caché semántico y rate limiting distribuido.
- **Pruebas**: `pytest` añadido y pruebas básicas en `backend/tests/test_basic.py` (chunking y redacción de PII).

## Ejecución de pruebas

Desde `backend/` (entorno con dependencias instaladas):
```bash
pytest -q
```

## Siguientes pasos sugeridos

- Integrar Redis para cuotas/caché real, métricas/logs estructurados y trazabilidad.
- Ampliar ingesta a más formatos (páginas/libros/foros, DOCX/PPTX con conversión) y mejorar citas con ubicación fina.
- Añadir pruebas de integración/end-to-end y pipeline CI.
- Endurecer proxy y políticas de acceso (timeouts, retries, auditoría).