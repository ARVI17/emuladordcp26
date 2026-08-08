# Mapa del proyecto

Referencia técnica del estado implementado de `emuladordcp26`. Se contrastó con el código fuente y con `/api/openapi.json`. El prefijo `/api` existe en el acceso por Nginx; las rutas declaradas en FastAPI y usadas por `TestClient` no lo incluyen.

## Alcance actual

La aplicación implementa:

- inventario local con CRUD, filtros, protección y eliminación lógica;
- importación revisable CSV/XLSX y exportación CSV/XLSX;
- OCR local de una captura, únicamente como vista previa;
- plantillas, duplicación, protección conjunta y recomendación simple 4-3-3;
- desafíos DCP con solver CP-SAT, simulación, confirmación y restauración;
- objetivos/evoluciones y perfil local;
- historial y chat de solo consulta con Ollama;
- control ADB local asistido: conexión TCP, captura/OCR, lectura revisable del club/requisitos DCP, toques, calibración y planes que preparan una combinación;
- auditoría de mutaciones relevantes;
- respaldo/restauración de PostgreSQL mediante scripts de PowerShell;
- SPA/PWA mobile-first con tema claro/oscuro.

La integración ADB está implementada, pero el proyecto no instala ni inicia un emulador Android: el usuario debe aportar un teléfono/emulador accesible por TCP e iniciar sesión por su cuenta. La sincronización es visual y revisable, no una API oficial de EA: no existe conexión autenticada, sincronización silenciosa, compra, venta ni entrega final automatizada. En el entorno actual `/api/emulator/status` informa `enabled=true`, `available=false` porque no hay dispositivo conectado. Tampoco hay precios de mercado externos.

## Arquitectura en ejecución

```text
Navegador/PWA
     |
     | http://localhost:${APP_PORT:-8080}
     v
Nginx de entrada
     |-- /, assets ----------> frontend:80 (Nginx + build Vite)
     |-- /api/*, /health ----> backend:8000 (FastAPI)
                                    |-- SQLAlchemy --> database:5432
                                    |                  (PostgreSQL 16)
                                    |
                                    |-- HTTP --------> ollama:11434
                                    |                  (opcional en uso)
                                    |
                                    |-- memoria -----> pandas/OpenCV/
                                    |                  Tesseract
                                    |
                                    `-- ADB TCP -----> host.docker.internal:5555
                                                       teléfono/emulador del usuario
```

Solo Nginx y PostgreSQL publican puertos en el host. Backend, frontend y Ollama permanecen en `emuladordcp26_internal`. El backend resuelve `host.docker.internal` mediante `extra_hosts: host-gateway` para iniciar conexiones ADB salientes al host. Nginx no depende de Ollama ni de un dispositivo ADB, por lo que la aplicación principal funciona si cualquiera de ellos no está disponible.

### Configuración

| Variable | Predeterminado | Consumidor |
| --- | --- | --- |
| `APP_PORT` | `8080` | puerto público de Nginx y scripts |
| `POSTGRES_PORT` | `55432` | puerto de PostgreSQL en el host |
| `POSTGRES_DB` | `fc26` | contenedor PostgreSQL/scripts |
| `POSTGRES_USER` | `fc26` | contenedor PostgreSQL/scripts |
| `POSTGRES_PASSWORD` | `fc26_local_change_me` | PostgreSQL y URL predeterminada |
| `DATABASE_URL` | PostgreSQL en `database:5432/fc26` | SQLAlchemy/Alembic |
| `DATABASE_POOL_SIZE` / `DATABASE_MAX_OVERFLOW` | `3` / `2` | máximo normal y excedente del pool SQLAlchemy |
| `POSTGRES_SHARED_BUFFERS` | `64MB` | memoria compartida de PostgreSQL |
| `POSTGRES_MAX_CONNECTIONS` | `30` | tope de sesiones PostgreSQL |
| `POSTGRES_WORK_MEM` / `POSTGRES_MAINTENANCE_WORK_MEM` | `2MB` / `32MB` | memoria por operación y mantenimiento |
| `OLLAMA_URL` | `http://ollama:11434` | servicio Ollama del backend |
| `OLLAMA_MODEL` | `qwen2.5:3b` | generación y estado de IA |
| `OLLAMA_KEEP_ALIVE` | `2m` | residencia equilibrada del modelo en Ollama y petición del backend |
| `OLLAMA_MAX_LOADED_MODELS` | `1` | máximo de modelos residentes |
| `OLLAMA_NUM_PARALLEL` | `1` | concurrencia de inferencia por modelo |
| `OLLAMA_CONTEXT_LENGTH` | `4096` | límite predeterminado de contexto |
| `OLLAMA_FLASH_ATTENTION` | `1` | reducción de memoria de contexto cuando el backend GPU lo admite |
| `OLLAMA_NO_CLOUD` | `1` | desactiva funciones remotas de Ollama y mantiene inferencia local |
| `*_MEMORY_LIMIT` | 64 MB–3 GB según servicio | límites defensivos de RAM en Compose |
| `CORS_ORIGINS` | localhost/127.0.0.1 en 8080 | middleware CORS |
| `MAX_UPLOAD_MB` | `10` | importaciones y OCR |
| `ADB_ENABLED` | `true` | habilita/deshabilita las órdenes del puente ADB |
| `ADB_DEFAULT_ADDRESS` | `host.docker.internal:5555` | dirección inicial guardada/mostrada para ADB TCP |
| `SEED_DEMO` | `true` | entrypoint del backend |
| `VITE_API_URL` | `/api` | cliente compilado del frontend |

Nginx admite hasta `12m`; el backend aplica además `MAX_UPLOAD_MB` (10 MB por defecto).

## Backend

### Arranque y composición

- `backend/entrypoint.sh`: si recibe un comando lo ejecuta directamente; en arranque normal aplica Alembic, ejecuta el seed opcional y arranca Uvicorn.
- `backend/app/main.py`: registra CORS, respuestas 422 simplificadas y un manejador 500 sin trazas públicas. Configura `root_path="/api"` para documentación detrás del proxy.
- `backend/app/core/config.py`: carga configuración de entorno con `pydantic-settings` y convierte `CORS_ORIGINS` en lista.
- `backend/app/db/session.py`: crea el engine y `SessionLocal`; habilita `check_same_thread=False` solo para SQLite de pruebas.
- `backend/app/api/routes.py`: contiene las operaciones generales, serializadores explícitos y límites de transacción.
- `backend/app/api/emulator.py`: router con prefijo `/emulator`; coordina ADB, configuración, OCR, sesiones de inventario y ejecución de planes.

### Módulos de dominio y servicios

| Archivo | Responsabilidad real |
| --- | --- |
| `models/entities.py` | Entidades SQLAlchemy, relaciones y valores predeterminados |
| `schemas/api.py` | Cuerpos Pydantic de entrada; no define modelos completos para todas las respuestas |
| `optimizers/sbc.py` | Candidatos, restricciones CP-SAT, función de coste, soluciones alternativas y revalidación |
| `services/rating.py` | Media `floor_average`, `round_half_up` o `ceiling` y suma mínima equivalente |
| `services/import_export.py` | CSV con biblioteca estándar, XLSX con pandas diferido, OCR OpenCV/Tesseract diferido, lectura estructurada y acotada de accesibilidad para inventario, y extracción heurística de requisitos DCP |
| `services/ollama.py` | `/api/tags`, `/api/generate` y respuesta degradada ante cualquier fallo |
| `services/adb.py` | cliente `subprocess` para ADB, validación de direcciones/seriales, captura/tamaño, entrada restringida y pasos de preparación DCP |
| `services/audit.py` | Agrega `AuditLog` a la sesión; la ruta llamante hace commit |
| `db/seed.py` | Demo idempotente controlada por la existencia de un `Profile` |

### Requisitos DCP aceptados

`Segment.requirements` es JSON. El solver y el validador reconocen:

| Clave | Significado |
| --- | --- |
| `squad_size` | cantidad exacta; predeterminado 11 |
| `min_rating` | media mínima según `rating_strategy` |
| `rating_strategy` | `floor_average` predeterminado, `round_half_up` o `ceiling` |
| `min_chemistry` | suma mínima del valor 0–3 almacenado en cada carta |
| `min_rare`, `min_special` | cantidades mínimas por bandera |
| `min_leagues`, `max_leagues` | cantidad de ligas distintas |
| `min_clubs`, `max_clubs` | cantidad de clubes distintos |
| `min_nations`, `max_nations` | cantidad de nacionalidades distintas |
| `required_league`, `min_from_league` | valor y cantidad mínima de una liga |
| `required_club`, `min_from_club` | valor y cantidad mínima de un club |
| `required_nation`, `min_from_nation` | valor y cantidad mínima de una nacionalidad |
| `required_card_type`, `min_card_type` | valor y cantidad mínima de un tipo de carta |
| `required_positions` | objeto `{posición: cantidad_mínima}` |
| `required_player_ids` | IDs que deben aparecer |
| `excluded_player_ids` | IDs que nunca pueden aparecer |
| `max_total_value` | tope para la suma de `Player.price` |

`OptimizeRequest` agrega `allow_protected_ids`, `exclude_ids` y `max_solutions` (1–5). Una autorización en `allow_protected_ids` permite simular con esa carta; la confirmación actual, sin embargo, rechaza cualquier carta que siga marcada `protected`. El frontend siempre envía listas de autorización/exclusión vacías.

La función objetivo `_cost` combina el precio con penalizaciones por transferible, exceso de media, utilidad, especial y titular, y bonificaciones por duplicado intransferible/baja utilidad. El `total_cost` de una solución es esta puntuación de optimización, no necesariamente gasto de mercado. `Submission.total_cost` sí guarda la suma directa de precios al confirmar.

Los valores de `AppSetting["optimizer"]` creados por el seed no alimentan todavía `_cost`; cambiar esos settings por API no reconfigura el solver.

## API HTTP

El OpenAPI actual contiene 54 operaciones, incluidas 20 bajo `/emulator`. Todos los paths de esta sección se consumen externamente como `/api<path>`, salvo el acceso cómodo `/health`, que Nginx también reenvía directamente. Swagger está en `/api/docs`.

### Salud y resumen

| Método y path | Entrada | Salida/efecto |
| --- | --- | --- |
| `GET /health` | — | verifica `select(1)` y devuelve estado, base y hora UTC |
| `GET /dashboard` | — | perfil, conteos, hasta 5 objetivos pendientes y alertas de duplicados/protegidos |

### Jugadores e inventario

| Método y path | Entrada | Salida/efecto |
| --- | --- | --- |
| `GET /players` | query `search`, `position`, `league`, `protected`, `duplicate`, `sort`, `order`, `limit` 1–500, `offset` | página `{items,total,limit,offset}`; excluye eliminados |
| `POST /players` | `PlayerCreate` | crea carta, audita `create`, devuelve 201 |
| `PATCH /players/{player_id}` | `PlayerUpdate` parcial | actualiza carta disponible y audita campos |
| `DELETE /players/{player_id}` | — | marca `deleted=true`, audita `soft_delete` |
| `POST /players/{player_id}/protect` | — | alterna `protected`, audita y devuelve carta |
| `GET /players/export` | query `format=csv|xlsx` | descarga solo cartas no eliminadas |
| `POST /players/import` | multipart `file`, form `confirm=false` | vista previa de hasta 100 filas o inserción total al confirmar |

Campos obligatorios para importar: `name,rating,position,league,club,nationality`. Campos opcionales reconocidos: `card_type,rare,special,tradable,price,chemistry,protected,duplicate_untradeable`. La importación no concilia ni desduplica filas.

### Duplicados y plantillas

| Método y path | Entrada | Salida/efecto |
| --- | --- | --- |
| `GET /duplicates` | — | cartas disponibles con `duplicate_untradeable=true`, ordenadas por media |
| `POST /duplicates/{player_id}/used` | — | pone `duplicate_untradeable=false` y audita |
| `GET /squads` | — | plantillas con jugadores, media calculada y química sumada |
| `POST /squads` | `SquadCreate {name,formation,player_ids}` | crea plantilla y slots `POS-1...`; no admite IDs repetidos/eliminados |
| `POST /squads/{squad_id}/duplicate` | — | copia plantilla, slots e IDs; no copia banderas primary/protected |
| `POST /squads/{squad_id}/protect` | — | alterna la protección de plantilla y de todas sus cartas |
| `POST /squads/recommend` | query opcional `formation` | escoge por media/química la primera carta por los 11 puestos fijos de 4-3-3 |

El parámetro `formation` de recomendación se refleja en la respuesta, pero la lista de posiciones está codificada para 4-3-3.

### Desafíos, segmentos y entregas

| Método y path | Entrada | Salida/efecto |
| --- | --- | --- |
| `GET /challenges` | — | desafíos con segmentos, primero no completados |
| `POST /challenges` | `ChallengeCreate` | crea cabecera y audita; 201 |
| `POST /challenges/{challenge_id}/segments` | `SegmentCreate {name,requirements}` | crea segmento JSON y audita; 201 |
| `POST /segments/{segment_id}/optimize` | `OptimizeRequest` | hasta 1–5 soluciones, mensaje si no existe ninguna y `simulation=true`; no escribe |
| `POST /segments/{segment_id}/confirm` | `ConfirmRequest {player_ids}` | revalida, consume lógicamente, completa segmento/desafío, crea snapshot y auditoría |
| `POST /submissions/{submission_id}/restore` | — | restaura flags guardados, reabre segmento/desafío y marca submission `restored` |

Confirmar exige IDs únicos y disponibles, rechaza protegidos y vuelve a ejecutar `validate_solution`. Restaurar una misma entrega dos veces devuelve 409.

### Objetivos y evoluciones

| Método y path | Entrada | Salida/efecto |
| --- | --- | --- |
| `GET /objectives` | — | objetivos ordenados por finalización y vencimiento |
| `POST /objectives` | `ObjectiveCreate` | crea y deriva `completed` de progreso/meta |
| `PATCH /objectives/{objective_id}` | `ObjectiveUpdate` parcial | actualiza; si no llega `completed`, lo recalcula |

Una evolución es un `Objective` con `category="Evolución"`; no hay tabla o motor independiente de evoluciones.

### Emulador asistido por ADB

| Método y path | Entrada | Salida/efecto |
| --- | --- | --- |
| `GET /emulator/status` | — | indica habilitación/disponibilidad, lista `adb devices -l`, configuración y mensaje degradado; no falla si no hay dispositivo |
| `POST /emulator/connect` | `EmulatorConnectRequest {address}` | ejecuta `adb connect`, guarda address/serial y audita `connect` |
| `POST /emulator/pair` | `EmulatorPairRequest {address,pairing_code}` | ejecuta `adb pair`; valida seis dígitos y audita solo dirección/que el código no se guardó |
| `GET /emulator/screenshot` | — | devuelve PNG en memoria con `Cache-Control: no-store` |
| `POST /emulator/inspect` | — | captura, OCR y tamaño de pantalla; devuelve `source="ADB"`, `saved=false` |
| `POST /emulator/dcp/inspect` | — | extrae requisitos frecuentes y devuelve un borrador revisable; no crea ni ejecuta el DCP |
| `POST /emulator/tap` | `EmulatorTapRequest {x,y}` | envía toque manual y audita `tap` |
| `POST /emulator/swipe` | `EmulatorSwipeRequest {x1,y1,x2,y2,duration_ms}` | envía deslizamiento manual y audita `swipe` |
| `GET /emulator/calibration` | — | devuelve calibración guardada o `null` |
| `PUT /emulator/calibration` | `EmulatorCalibration` | valida resolución/coordenadas, guarda en `AppSetting["emulator"]` y audita `calibrate` |
| `GET /emulator/scans` | query `limit` 1–100 | sesiones recientes con candidatos/progreso, nunca imágenes |
| `POST /emulator/scans` | — | exige dispositivo listo y crea una sesión ligada a serial/resolución; 201 |
| `POST /emulator/scans/{scan_id}/continue` | — | después del límite crea otro lote ligado a la huella de la última página, sin copiar candidatos |
| `POST /emulator/scans/{scan_id}/capture` | — | captura temporal; prioriza filas de accesibilidad y usa OCR como respaldo, rechaza la misma página y acumula candidatos revisables |
| `POST /emulator/scans/{scan_id}/advance` | — | valida pantalla/lista/botón, desplaza, pulsa únicamente `Siguiente`, verifica que cambió la página y añade hasta 20 filas estructuradas |
| `POST /emulator/scans/{scan_id}/import` | `InventoryScanImportRequest` | exige frase y `candidate_ids`; importa hasta 500 revisados, retira solo esos candidatos y opcionalmente archiva nombres exactos de la demo |
| `POST /emulator/scans/{scan_id}/cancel` | — | cierra una sesión no importada |
| `GET /emulator/plans` | query `limit` 1–100 | últimos planes, más recientes primero |
| `POST /emulator/plans` | `AutomationPlanCreate {segment_id,player_ids}` | revalida combinación, rechaza protegidos y crea plan `draft` con snapshot; 201 |
| `POST /emulator/plans/{plan_id}/prepare` | — | exige calibración, revalida, copia calibración al snapshot, genera pasos, fija dispositivo y cambia a `prepared` |
| `POST /emulator/plans/{plan_id}/execute` | `AutomationExecuteRequest {confirmation}` | exige `PREPARAR <id>`, revalida, comprueba dispositivo/resolución/exclusión mutua, encola y agenda tarea de fondo |
| `POST /emulator/plans/{plan_id}/cancel` | — | cambia a `cancelled`, salvo que ya esté `completed` |

Los cuerpos aplican estos límites:

- address: `host:puerto`, con caracteres alfanuméricos, `.`, `_` o `-`, puerto escrito con 2–5 dígitos y valor numérico 1–65535;
- coordenadas: 0–10000; la calibración exige pantalla de al menos 240×320 y que cada punto quede dentro de ella;
- `duration_ms`: 100–3000; `wait_ms`: 250–5000;
- plan: 1–23 IDs únicos, existentes, no eliminados, no protegidos y todavía válidos para el segmento;
- confirmación: comparación sin distinguir mayúsculas/espacios externos con `PREPARAR <id>`.

`plan_data` expone `confirmation_phrase` únicamente en estado `prepared` y siempre devuelve `final_submission_automated=false`. Las operaciones auditadas son conexión, toques/deslizamientos manuales, calibración y creación/preparación/aprobación/cancelación de planes. Cada paso terminado agrega `execute_step`; un fallo agrega `execute_failed`, además de estado/error. La ejecución no crea una `Submission` y no altera `Player.deleted` ni `Segment.completed`.

`emulator_config` y `save_emulator_config` copian el diccionario JSON para que SQLAlchemy detecte de forma segura los cambios de address/serial/calibración. Al ejecutar se rechaza otro `AutomationPlan` `queued` o `running` con el mismo `device_serial`. El serial debe aparecer en `adb devices` con estado `device`, y `screen_size` debe coincidir con la calibración guardada tanto antes de encolar como al empezar la tarea de fondo.

`InventoryScan` limita 50 páginas, 1000 candidatos y 500 jugadores por solicitud de importación. La lectura estructurada valida el título `Futb. de Mi Club`, clases/estado/límites del botón y serial/resolución; el XML temporal se limita a 2 MB, se elimina del dispositivo y nunca se persiste o devuelve. Guarda SHA-256 de la imagen o de la firma estructurada para evitar páginas idénticas y no persiste PNG ni `raw_text`. `IMPORTAR <id>` agrega únicamente los `candidate_ids` seleccionados y deja el resto en `review` para otro lote; `REEMPLAZAR DEMO <id>` además marca `deleted=true` únicamente para los 132 nombres deterministas del seed.

### IA, OCR, perfil, settings y auditoría

| Método y path | Entrada | Salida/efecto |
| --- | --- | --- |
| `GET /ai/status` | — | disponibilidad de Ollama y modelo configurado |
| `POST /ai/chat` | `ChatRequest {message}` (1–2000) | envía pregunta + resumen agregado, persiste ambos mensajes y audita |
| `GET /ai/history` | query `limit` 1–200 | últimos mensajes devueltos en orden cronológico |
| `POST /ocr/preview` | multipart `file` JPEG/PNG/WebP | texto máximo 5000 caracteres, un candidato y `requires_confirmation=true`; no persiste |
| `GET /profile` | — | primer perfil local |
| `PATCH /profile` | `ProfileUpdate` parcial | actualiza y audita |
| `GET /settings` | — | diccionario `{key: value}` |
| `PUT /settings/{key}` | cuerpo JSON objeto | upsert de clave alfanumérica/guion bajo, máximo 80 caracteres |
| `GET /audit` | query `limit` 1–200 | últimos eventos, de más nuevo a más antiguo |

El chat resume conteo total, duplicados, protegidos y hasta 10 nombres de DCP pendientes. No entrega registros completos a Ollama y no ejecuta herramientas ni mutaciones basadas en la respuesta.

## Persistencia

Head de Alembic: `0004` (`0001` crea el esquema inicial, `0002` agrega chat, `0003` crea `automation_plans` y `0004` crea `inventory_scans`).

| Modelo / tabla | Campos y relaciones relevantes |
| --- | --- |
| `Profile` / `profiles` | nombre, monedas, plataforma, presupuesto, riesgo, preferencias JSON; se usa el primer registro |
| `Player` / `players` | identidad deportiva, media, posición, liga/club/nación, tipo/rareza, transferibilidad/precio/química, protección/titular/rol/utilidad/duplicado, `deleted`, timestamps |
| `Squad` / `squads` | nombre, formación, primary/protected; relación 1:N con `SquadPlayer` |
| `SquadPlayer` / `squad_players` | FK a plantilla y jugador, slot; único por `(squad_id,slot)`; cascade al borrar plantilla |
| `Challenge` / `challenges` | nombre, descripción, recompensa, completado, vencimiento; relación 1:N con segmentos |
| `Segment` / `segments` | FK a desafío, nombre, requisitos JSON, completado; cascade al borrar desafío |
| `Submission` / `submissions` | FK a segmento, estado, coste, snapshot JSON, fecha; soporte de restauración |
| `Objective` / `objectives` | nombre, descripción, categoría, progreso, meta, completado, vencimiento |
| `AuditLog` / `audit_logs` | acción, tipo/ID de entidad, detalles JSON, fecha |
| `AppSetting` / `app_settings` | clave primaria string y valor JSON |
| `ChatMessage` / `chat_messages` | rol, contenido, metadata JSON, fecha |
| `AutomationPlan` / `automation_plans` | nombre/tipo/estado, serial, FK opcional a segmento, IDs, snapshot y pasos JSON, progreso/error, aprobación/ejecución/creación |
| `InventoryScan` / `inventory_scans` | estado, serial/resolución, páginas/hashes/candidatos JSON, IDs y conteo importados, error y fechas |

Relaciones principales:

```text
Squad 1 ---- * SquadPlayer * ---- 1 Player
Challenge 1 -------------------- * Segment
Segment 1 ---------------------- * Submission
Segment 1 ---------------------- * AutomationPlan
```

`Player` no se borra al confirmar un DCP: queda con `deleted=true`. El snapshot de `Submission` conserva por jugador los valores anteriores de `deleted` y `duplicate_untradeable`, suficientes para el flujo de restauración implementado.

`AutomationPlan.solution_snapshot` conserva jugadores ordenados, requisitos y las banderas `validated=true`/`delivery_requires_manual_confirmation=true`; `steps` contiene el plan concreto generado desde la calibración. No hay relación ORM declarada hacia `Segment`, aunque sí FK en la tabla.

### Seed demostrativo

Cuando no existe ningún perfil, `seed_database()` crea:

- 1 perfil `Club Local`;
- 132 jugadores ficticios, incluidos 11 titulares protegidos y 8 duplicados intransferibles;
- 1 plantilla principal 4-3-3 protegida;
- 5 desafíos con 7 segmentos totales;
- 8 objetivos y 2 evoluciones;
- settings informativos para `optimizer` y `ollama`.

La presencia de cualquier perfil detiene todo el seed.

## Frontend

### Estructura

- `main.tsx`: crea `QueryClient`, registra el service worker y monta `App`.
- `App.tsx`: navegación, páginas, formularios y mutaciones. No hay React Router; la página activa vive en estado.
- `api/client.ts`: `API_URL`, wrapper `fetch`, `ApiError`, formato monetario `es-CO` y fechas cortas.
- `types/index.ts`: tipos de dominio y contratos de dispositivo, calibración, planes, `InventoryScan` y `DcpInspection`.
- `styles.css`: layout, componentes, temas y adaptación móvil.
- `vite.config.ts`: React, Vitest y PWA `autoUpdate` con manifiesto e icono SVG.

TanStack Query usa `staleTime=15s`, un reintento en consultas y cero reintentos en mutaciones.

### Pantallas y dependencias HTTP

| Pantalla | Lecturas | Mutaciones/acciones |
| --- | --- | --- |
| Inicio | `/dashboard` | navegación interna |
| Club | `/players` | crear, editar, proteger, eliminar, revisar/confirmar importación, exportar |
| Plantillas | `/squads` | recomendar, guardar recomendación, duplicar, proteger completa |
| DCP | `/challenges` | crear desafío+segmento, optimizar, crear plan con **Preparar en emulador**, confirmar entrega local con diálogo |
| Objetivos | `/objectives` | crear, sumar progreso, completar |
| Duplicados | `/duplicates`, `/challenges` | marcar duplicado utilizado |
| IA | `/ai/status` cada 30s, `/ai/history` | enviar chat |
| Emulador | estado/lecturas cada 5s, planes cada 2,5s | conectar, capturar, calibrar por clic, leer DCP/club, revisar/importar y preparar/ejecutar/cancelar planes |
| Ajustes | `/profile` | editar perfil, cambiar tema local, OCR preview, restaurar submission |

La UI de creación de DCP solo expone `squad_size=11`, `min_rating`, `min_chemistry` y `min_rare`. Los requisitos avanzados solo están accesibles por API. Cada solución ofrece **Preparar en emulador**, que crea un plan pero no lo ejecuta. La UI de OCR muestra el candidato, pero no lo transfiere automáticamente al formulario de Club.

La pantalla activa `CompanionPage` parte de una calibración 1080×2400. Un clic normal toca el dispositivo, pero seleccionar un objetivo de calibración convierte el siguiente clic en medición local sin enviar pulsación. También acumula sesiones de inventario y crea borradores DCP desde OCR. Para un plan `prepared`, la ejecución permanece deshabilitada hasta que la entrada coincida con `PREPARAR <id>`.

## Flujos de datos

### Arranque

```text
Compose inicia database
  -> espera health de PostgreSQL
  -> backend ejecuta alembic upgrade head
  -> seed opcional comprueba Profile
  -> Uvicorn queda healthy
  -> frontend queda healthy
  -> Nginx habilita el acceso público
```

### Importación

```text
Usuario selecciona CSV/XLSX
  -> POST /players/import confirm=false
  -> límite + extensión + columnas + conversión
  -> vista previa (máximo 100 filas, sin escritura)
  -> usuario confirma
  -> POST del mismo archivo confirm=true
  -> inserta todas las filas + AuditLog + commit
  -> invalida inventario y dashboard
```

No se conserva el archivo, no hay upsert y no se compara con el inventario existente.

### OCR

```text
JPEG/PNG/WebP
  -> límite MIME/tamaño
  -> cv2.imdecode -> escala de grises -> resize 1.6x -> Otsu
  -> Tesseract spa+eng
  -> regex de media/posición + primera línea como nombre
  -> respuesta de revisión
```

No se escribe en disco ni en PostgreSQL.

### DCP

```text
Segment.requirements + jugadores no eliminados
  -> excluir IDs bloqueados y protegidos no autorizados
  -> CP-SAT minimiza _cost (máximo 8s, 4 workers)
  -> bloquea la combinación anterior para alternativas
  -> validate_solution descarta cualquier resultado inválido
  -> respuesta simulation=true, sin commit

Usuario elige y confirma
  -> vuelve a consultar IDs disponibles
  -> rechaza repetidos/protegidos
  -> validate_solution otra vez
  -> snapshot
  -> Player.deleted=true y duplicate_untradeable=false
  -> Segment/Challenge.completed
  -> Submission + AuditLog + commit

Usuario restaura por submission_id
  -> recupera flags del snapshot
  -> reabre segmento/desafío
  -> Submission.status=restored + AuditLog + commit
```

### Preparación ADB de una combinación

```text
Solución optimizada
  -> usuario pulsa "Preparar en emulador"
  -> POST /emulator/plans revalida segmento y cartas
  -> AutomationPlan draft + snapshot + AuditLog

Usuario conecta dispositivo y guarda calibración
  -> AppSetting["emulator"] conserva address/serial/calibration
  -> POST /plans/{id}/prepare
  -> revalida jugadores/segmento
  -> copia calibración al solution_snapshot
  -> build_dcp_steps crea 9 pasos por jugador
  -> plan prepared + frase PREPARAR <id>

Usuario revisa y escribe la frase exacta
  -> revalida jugadores/segmento otra vez
  -> verifica serial conectado y resolución calibrada
  -> rechaza otro plan queued/running para el mismo serial
  -> plan queued + approved_at + tarea FastAPI BackgroundTasks
  -> plan running
  -> vuelve a comprobar resolución al comenzar
  -> tap/wait/tap/text/wait/tap/wait/tap/wait por jugador
  -> progress_step + AuditLog execute_step después de cada paso
  -> completed + executed_at, failed + last_error/execute_failed, o cancelled
  -> usuario revisa la plantilla y decide manualmente si entrega
```

`build_dcp_steps` solo abre búsqueda, activa el campo, escribe un nombre saneado, selecciona el primer resultado y agrega la carta. Para 11 jugadores genera 99 pasos. No comprueba visualmente que el primer resultado sea la carta correcta y no genera ningún toque de **Enviar/Entregar DCP**. `run_step` admite internamente `tap`, `swipe`, `text`, `keyevent` de una lista reducida y `wait`, pero los planes DCP generados actualmente solo contienen `tap`, `text` y `wait`.

### Lectura visual del inventario

```text
Usuario abre Mi club e inicia InventoryScan
  -> fija serial + resolución
  -> lee jerarquía temporal acotada -> nombre/media/posición de hasta 20 filas
  -> si no existe esa estructura: captura PNG en memoria -> SHA-256 -> OCR conservador
  -> descarta XML/PNG y persiste solo firma/candidatos/progreso
  -> “Avanzar y leer siguiente” valida pantalla + botón + cambio de página
  -> al llegar a 50 páginas/1000 candidatos puede crear un lote de continuación
  -> usuario corrige/selecciona
  -> frase IMPORTAR <id> o REEMPLAZAR DEMO <id>
  -> crea Player + AuditLog; opcionalmente archiva solo nombres demo
```

Estados posibles:

```text
draft -> prepared -> queued -> running -> completed
   |         |          |         |
   `---------+----------+---------+-> cancelled
                                  `-> failed
```

Un plan `running` revisa entre pasos si fue cancelado. Un plan `completed` no puede cancelarse. `completed` significa preparación terminada, no entrega realizada.

### Protección de plantilla

Alternar `/squads/{id}/protect` cambia `Squad.protected` y aplica el mismo booleano a todas las cartas relacionadas. Desproteger la plantilla también desprotege esas cartas aunque hubieran sido protegidas individualmente antes; no existe snapshot de protecciones previas para este flujo.

### Ollama

```text
Pregunta
  -> conteos agregados + nombres de DCP pendientes
  -> comprobación GET /api/tags (timeout 1.5s)
  -> POST /api/generate sin streaming (timeout 45s)
  -> respuesta o mensaje degradado
  -> persiste mensaje del usuario + respuesta + auditoría
```

La respuesta degradada también se guarda en el historial.

### Respaldo/restauración

`scripts/backup.ps1` crea en `backups/` un dump PostgreSQL, un CSV adicional del inventario y un JSON de settings. `scripts/restore.ps1` solo acepta `.dump` dentro de esa carpeta, crea primero `before-restore-*.dump`, ejecuta `pg_restore --clean --if-exists --no-owner` y reinicia backend. `scripts/export-data.ps1` exporta inventario CSV/XLSX y settings sin dump.

`scripts/check-emulator.ps1` valida una dirección, exige que el backend esté iniciado, muestra `adb devices -l` desde el contenedor y consulta `/api/emulator/status`. Con `-Connect` intenta antes `adb connect <Address>`. El valor predeterminado es `host.docker.internal:5555`.

## Pruebas existentes

### Backend: 30 casos Pytest

`backend/tests/conftest.py` fija SQLite temporal antes de importar la aplicación, reconstruye todas las tablas y ejecuta el seed por caso.

- `test_api.py`: health/seed/dashboard, CRUD/protección, plantillas, objetivos, CSV y degradación de Ollama/historial.
- `test_optimizer.py`: solución válida, caso imposible, simulación/confirmación/restauración, rechazo de protegidos y bonificación de duplicados.
- `test_emulator.py`: 17 casos para degradación, validación/emparejamiento ADB sin fuga de código, planes/frases/auditoría, ausencia de submit final, sesión de inventario, accesibilidad temporal acotada, avance validado, continuación limitada, importación parcial por IDs, captura repetida, reemplazo de demo y extractores revisables.
- `test_rating.py`: tres estrategias y suma mínima por estrategia.

### Frontend

- Vitest: 2 casos para formato monetario y fecha ausente.
- Playwright: 2 casos iPhone 13; navegación/panel y pantalla Emulador con su aviso de entrega manual.
- `npm run build`: TypeScript y compilación Vite ocurren al construir la imagen frontend.

### Cobertura que todavía no existe

No hay pruebas directas para XLSX, OCR sobre una pantalla real de Companion, settings/audit completos, restauración de dump, PWA offline, múltiples tamaños de pantalla, Ollama disponible ni ejecución ADB contra un dispositivo real. Las pruebas simulan el bridge y validan seguridad/contratos, pero no demuestran compatibilidad visual con una versión concreta de Companion.

## Archivos operativos y datos generados

- `backups/`: dumps/exportaciones, ignorados salvo `.gitkeep`.
- `data/uploads/`: reservado e ignorado salvo `.gitkeep`; el OCR actual no guarda allí.
- `.env`: configuración local ignorada; `.env.example` es la plantilla versionable.
- `test_fc26.db`: SQLite de pruebas ignorado.
- `node_modules/`, `dist/`, cachés y cobertura: ignorados.

## Documentación relacionada

- [`ARCHITECTURE.md`](ARCHITECTURE.md): resumen por capas.
- [`OPTIMIZER.md`](OPTIMIZER.md): decisiones del solver y aproximación de media/química.
- [`SECURITY.md`](SECURITY.md): límites de confianza y controles locales.
- [`TESTING.md`](TESTING.md): comandos y verificación manual.
- [`USER_GUIDE.md`](USER_GUIDE.md): recorrido funcional para usuario.
- [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md): capacidades que no deben sobreafirmarse.
- [`../AGENTS.md`](../AGENTS.md): reglas de trabajo obligatorias para agentes futuros.
