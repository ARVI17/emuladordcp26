# Arquitectura

## Flujo

El navegador entra por Nginx en el puerto configurable `APP_PORT`. `/` se dirige al frontend estático y `/api/*` a FastAPI. El backend es el único servicio que accede a PostgreSQL, consulta Ollama por la red interna y ejecuta el cliente ADB. Un dispositivo Android es opcional y se conecta por TCP mediante `host.docker.internal`.

## Capas

- `frontend/src`: SPA React/PWA, consultas TanStack Query, formularios validados y diseño mobile-first.
- `backend/app/api`: endpoints y orquestación HTTP.
- `backend/app/models` y `schemas`: persistencia SQLAlchemy y contratos Pydantic.
- `backend/app/services`: cálculo de media, importación/exportación, OCR, Ollama, ADB y auditoría.
- `backend/app/optimizers`: modelo CP-SAT y validador independiente.
- `backend/alembic`: evolución reproducible del esquema.
- `scripts`: respaldo y restauración locales.

PostgreSQL conserva perfil, jugadores, plantillas, DCP, entregas reversibles, objetivos, configuración, auditoría, historial de chat y planes ADB con su progreso. Los archivos de carga y capturas se procesan en memoria; no se conservan después de responder.

Compose fija el nombre de proyecto `emuladordcp26`, contenedores propios, red `emuladordcp26_internal` y volúmenes propios. Ollama se inicia como servicio normal, pero la descarga del modelo se hace una sola vez y queda en `emuladordcp26_ollama_data`.

## Preparación ADB

`api/emulator.py` separa estado/conexión, captura/OCR, calibración y planes. `services/adb.py` ejecuta únicamente una lista restringida de órdenes (`tap`, `swipe`, `text`, `keyevent`, espera y captura), valida direcciones y seriales, y genera pasos sin acción de entrega. Un plan se construye desde una solución DCP revalidada, exige la frase `PREPARAR <id>` y avanza en una tarea de fondo cancelable. La configuración de coordenadas se guarda en `app_settings`; el plan y su snapshot quedan en `automation_plans`. Cada acción relevante genera auditoría.

## Inicialización

El entrypoint aplica `alembic upgrade head`, ejecuta un seed idempotente y arranca Uvicorn. Las dependencias de Compose esperan health checks. El seed detecta el perfil existente y no duplica información.
