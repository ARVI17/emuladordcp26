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

PostgreSQL conserva perfil, jugadores, plantillas, DCP, entregas reversibles, objetivos, configuración, auditoría, historial de chat, planes ADB y sesiones de lectura. Las imágenes y jerarquías temporales se procesan en memoria; `inventory_scans` solo conserva hashes/firmas, candidatos revisables, progreso e IDs importados.

Compose aplica límites defensivos de memoria por servicio. PostgreSQL usa buffers y conexiones ajustados para una aplicación local y SQLAlchemy mantiene un pool pequeño. Ollama reserva una GPU NVIDIA, mantiene como máximo un modelo y lo descarga después del periodo corto configurado; el backend sigue degradándose de forma segura si la GPU u Ollama no están disponibles. Las dependencias de OCR, XLSX y CP-SAT se importan al utilizar su función para mantener bajo el consumo del backend durante el reposo. El Nginx del frontend usa un solo worker porque sirve únicamente archivos estáticos detrás del proxy de entrada.

Compose fija el nombre de proyecto `emuladordcp26`, contenedores propios, red `emuladordcp26_internal` y volúmenes propios. Ollama se inicia como servicio normal, pero la descarga del modelo se hace una sola vez y queda en `emuladordcp26_ollama_data`.

## Preparación ADB

`api/emulator.py` separa estado/conexión, captura/lectura, calibración y planes. `services/adb.py` ejecuta únicamente una lista restringida de órdenes (`tap`, `swipe`, `text`, `keyevent`, espera, captura y lectura temporal de UI), valida direcciones y seriales, y genera pasos sin acción de entrega. La navegación de inventario solo actúa tras validar título, botón habilitado, límites, resolución y cambio de filas. Un plan se construye desde una solución DCP revalidada, exige la frase `PREPARAR <id>` y avanza en una tarea de fondo cancelable. La configuración de coordenadas se guarda en `app_settings`; el plan y su snapshot quedan en `automation_plans`. Cada acción relevante genera auditoría.

Las sesiones `InventoryScan` exigen un dispositivo conectado y resolución estable. Companion se lee primero mediante una jerarquía de accesibilidad limitada a 2 MB y eliminada inmediatamente; si la estructura esperada no existe, una captura en memoria usa OCR. Cada página se identifica por SHA-256 de imagen o firma de cartas. Los lotes mantienen el máximo de 50 páginas/1000 candidatos y pueden continuar sin copiar la última página. Importar exige `IMPORTAR <id>`; archivar las cartas demo exige `REEMPLAZAR DEMO <id>`. La lectura de requisitos DCP produce únicamente un borrador local revisable.

## Inicialización

El entrypoint aplica `alembic upgrade head`, ejecuta un seed idempotente y arranca Uvicorn. Las dependencias de Compose esperan health checks. El seed detecta el perfil existente y no duplica información.
