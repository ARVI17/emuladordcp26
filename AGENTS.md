# Guía persistente para agentes Codex

Este archivo es la entrada rápida para cualquier agente que trabaje en `emuladordcp26`. Lee también [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md) antes de cambiar arquitectura, datos o contratos HTTP.

## Propósito y estado real

`emuladordcp26` es una aplicación local y no oficial para administrar inventario revisado por el usuario, acumular lecturas OCR del club mostrado en Companion, organizar plantillas y objetivos, simular/confirmar/restaurar DCP y preparar combinaciones mediante pulsaciones ADB asistidas. La solución usa una SPA React, una API FastAPI, PostgreSQL, OR-Tools, un puente ADB y un chat opcional con Ollama, todo orquestado con Docker Compose.

El backend sí incluye el cliente ADB y puede conectar por TCP con un teléfono o emulador Android iniciado por el usuario, capturar/inspeccionar su pantalla, proponer inventario/requisitos, enviar toques y deslizamientos manuales, y ejecutar un plan revisable que busca y agrega los jugadores de una solución DCP. No instala ni inicia el emulador en el host, no se conecta a una API autenticada de EA y nunca automatiza el botón final de entrega, compras, ventas, inicio de sesión ni credenciales. En el entorno actual no hay ningún dispositivo/emulador conectado.

## Inicio rápido

Desde la raíz:

```powershell
docker compose up --build -d
docker compose ps
```

Accesos predeterminados:

- Aplicación: `http://localhost:8080`
- OpenAPI/Swagger: `http://localhost:8080/api/docs`
- Health externo: `http://localhost:8080/health`
- PostgreSQL del host: `localhost:55432`

Ollama arranca como servicio normal de Compose, pero una instalación nueva necesita descargar el modelo una vez:

```powershell
docker compose exec ollama ollama pull qwen2.5:3b
```

Compose limita RAM por servicio y reserva una GPU NVIDIA para Ollama. El modelo se descarga tras el periodo equilibrado de `OLLAMA_KEEP_ALIVE`; verifica la aceleración después de una consulta con `docker compose exec ollama ollama ps`. Los límites se pueden ajustar mediante las variables `*_MEMORY_LIMIT` de `.env.example` sin editar Compose.

En la estación Windows actual, `%USERPROFILE%\.wslconfig` limita globalmente WSL2 a 5 GB de RAM y 2 GB de swap con `autoMemoryReclaim=dropCache`. El valor protege memoria para el emulador Android; no lo reduzcas por debajo de 5 GB sin repetir Pytest, Playwright, OCR y una inferencia GPU.

La ausencia del modelo o una caída de Ollama no debe bloquear inventario, DCP, objetivos ni el resto de la aplicación.

## Comandos habituales

```powershell
# Construir/iniciar y detener sin borrar volúmenes
docker compose up --build -d
docker compose down

# Estado y diagnóstico
docker compose ps
docker compose logs --tail=200 backend database nginx frontend ollama

# Pruebas completas
docker compose run --rm --no-deps backend pytest -q
docker compose run --rm frontend-test
docker compose run --rm frontend-e2e

# Verificar migraciones y datos con el stack activo
docker compose exec backend alembic current
docker compose exec backend alembic check
docker compose exec database psql -U fc26 -d fc26 -c "select count(*) from players;"

# Seed idempotente
docker compose exec backend python -m app.db.seed

# Respaldo y restauración en Windows
powershell -ExecutionPolicy Bypass -File scripts/backup.ps1
powershell -ExecutionPolicy Bypass -File scripts/restore.ps1 -BackupFile backups/archivo.dump

# Diagnóstico ADB (agrega -Connect para intentar conectar)
powershell -ExecutionPolicy Bypass -File scripts/check-emulator.ps1
powershell -ExecutionPolicy Bypass -File scripts/check-emulator.ps1 -Connect -Address host.docker.internal:5555
```

`make up`, `make down`, `make logs`, `make test`, `make seed`, `make backup` y `make restore FILE=...` envuelven los mismos flujos. `make reset` ejecuta `docker compose down -v` y **borra los volúmenes**; no lo uses sin autorización explícita y un respaldo si hay datos reales.

## Topología Docker

| Servicio | Función | Exposición |
| --- | --- | --- |
| `nginx` | Único punto de entrada; enruta `/` al frontend y `/api/*` al backend | `${APP_PORT:-8080}:80` |
| `frontend` | Compila React/Vite/PWA y sirve estáticos con Nginx | solo red interna, puerto 80 |
| `backend` | FastAPI, SQLAlchemy, OR-Tools, OCR, cliente Ollama y cliente ADB | solo red interna, puerto 8000 |
| `database` | PostgreSQL 16 | `${POSTGRES_PORT:-55432}:5432` |
| `ollama` | Inferencia local mediante HTTP | solo red interna, puerto 11434 |
| `frontend-test` | Vitest, perfil `test` | efímero |
| `frontend-e2e` | Playwright con iPhone 13, perfil `test` | efímero |

Recursos dedicados: red `emuladordcp26_internal`, volumen `emuladordcp26_postgres_data` y volumen `emuladordcp26_ollama_data`. No reutilices nombres, redes o volúmenes de otros proyectos. El backend usa `extra_hosts: host.docker.internal:host-gateway` para alcanzar por TCP un ADB ejecutado en el host; `ADB_ENABLED` y `ADB_DEFAULT_ADDRESS` controlan esa integración.

El entrypoint del backend ejecuta `alembic upgrade head`, luego el seed si `SEED_DEMO=true`, y finalmente Uvicorn. El seed se detiene si ya existe un perfil, por lo que no duplica la demo.

## Mapa de código

- `docker-compose.yml`: servicios, health checks, variables, montajes y recursos dedicados.
- `nginx/nginx.conf`: proxy público, límite de carga y cabeceras de seguridad.
- `backend/app/main.py`: creación de FastAPI, CORS y manejadores globales de error.
- `backend/app/api/routes.py`: rutas generales y orquestación de sus transacciones.
- `backend/app/api/emulator.py`: estado/conexión ADB, captura/OCR, lectura de inventario/requisitos, toques, calibración y ciclo de planes.
- `backend/app/models/entities.py`: 13 modelos SQLAlchemy, incluidos `AutomationPlan` e `InventoryScan`.
- `backend/app/schemas/api.py`: entradas Pydantic y sus límites.
- `backend/app/optimizers/sbc.py`: modelo CP-SAT, función de coste y validación final de DCP.
- `backend/app/services/rating.py`: aproximaciones de media.
- `backend/app/services/import_export.py`: CSV/XLSX y OCR en memoria.
- `backend/app/services/ollama.py`: estado y generación con degradación segura.
- `backend/app/services/adb.py`: ejecución ADB validada, captura, entrada permitida y generación/ejecución de pasos DCP.
- `backend/app/services/audit.py`: creación de eventos de auditoría dentro de la transacción llamante.
- `backend/app/db/session.py`: engine y sesiones.
- `backend/app/db/seed.py`: demo idempotente.
- `backend/alembic/versions/`: esquema reproducible; head actual `0004` (`inventory_scans`).
- `frontend/src/App.tsx`: todas las vistas y mutaciones de la SPA.
- `frontend/src/api/client.ts`: prefijo `/api`, errores y formatos locales.
- `frontend/src/types/index.ts`: contratos TypeScript consumidos por la UI.
- `frontend/src/styles.css`: sistema visual mobile-first y temas.
- `frontend/vite.config.ts`: Vitest y manifiesto PWA.
- `backend/tests/`, `frontend/src/**/*.test.ts` y `frontend/e2e/`: pruebas automatizadas.
- `scripts/`: respaldo, restauración, exportación y diagnóstico ADB desde PowerShell.

Consulta el inventario detallado de rutas, entidades, pantallas y flujos en [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).

## Invariantes de seguridad y producto

Estas reglas forman parte del alcance actual y no deben relajarse incidentalmente:

1. No solicitar, almacenar ni registrar credenciales, cookies, tokens, OAuth o códigos de EA/FC Companion.
2. No afirmar conexión API con el club real. ADB lee/controla visualmente el dispositivo del propietario y puede acumular candidatos revisables, pero no hay API autenticada, scraping autenticado ni sincronización oficial de la cuenta.
3. La automatización asistida puede capturar, inspeccionar, tocar, deslizar y preparar una combinación ya validada. No debe añadir compras, ventas, partidos, login ni la pulsación final de entrega como efecto secundario de una consulta, cálculo o plan.
4. Optimizar un DCP es una simulación sin escrituras. Confirmar debe volver a validar contra el estado actual, requerir una acción explícita del usuario, rechazar cartas protegidas y guardar un snapshot restaurable.
5. Las cartas consumidas o eliminadas usan `Player.deleted`; no convertir estos flujos en borrado físico sin migración, respaldo y autorización clara.
6. Las capturas OCR se procesan en memoria y siempre exigen revisión. No persistir la imagen ni crear cartas automáticamente. `InventoryScan` puede conservar hashes, candidatos y progreso, nunca bytes de imagen ni texto de credenciales.
7. La importación CSV/XLSX primero presenta una vista previa; solo `confirm=true` escribe. Mantener validación de extensión, esquema, tamaño y rangos.
8. No exponer el stack directamente a Internet: no tiene autenticación multiusuario. Una publicación exige primero TLS, autenticación, secretos seguros y firewall.
9. No devolver trazas o detalles internos al cliente. Registrar el error localmente y conservar respuestas públicas genéricas.
10. Mantener CORS restringido, consultas ORM parametrizadas, límites de carga y las cabeceras CSP/`nosniff`/`SAMEORIGIN`/Referrer-Policy.
11. Ollama solo recibe un resumen controlado del inventario, no acceso directo a la base ni capacidad de mutación.
12. La media y la química son aproximaciones locales. No presentarlas como fórmula oficial garantizada de EA.
13. Un plan ADB exige calibración y la frase exacta `PREPARAR <id>` antes de ejecutarse. Justo antes de encolarlo vuelve a validar jugadores/requisitos, presencia del serial, resolución y ausencia de otro plan `queued`/`running` para ese dispositivo. Debe conservar `final_submission_automated=false`, poder cancelarse antes de terminar y generar únicamente pasos previos a la entrega irreversible.
14. Las coordenadas son absolutas para una resolución/pantalla concretas. Un cambio de resolución, orientación, escala o interfaz obliga a recalibrar y revisar manualmente.
15. Una lectura de inventario exige dispositivo/resolución estables, ignora hashes repetidos y limita 50 pantallas/1000 candidatos. Importar hasta 500 cartas exige `IMPORTAR <id>`; archivar solo nombres demo exige `REEMPLAZAR DEMO <id>`.
16. Los requisitos detectados por OCR son un borrador local. Nunca tratarlos como restricciones verificadas hasta revisión humana.
17. `POST /emulator/pair` acepta únicamente código temporal ADB de seis dígitos. Puede usarlo como argumento de proceso, pero nunca persistirlo, devolverlo, incluirlo en errores propios ni auditarlo.

Los estados persistidos de un plan son `draft`, `prepared`, `queued`, `running`, `completed`, `failed` y `cancelled`. `completed` significa únicamente que terminó la colocación prevista; nunca significa que el DCP fue entregado. Las rutas de conexión, toque/deslizamiento manual, calibración y cambios de plan relevantes se auditan; cada paso ejecutado crea un `AuditLog` `execute_step`, y un error crea `execute_failed` además de persistir `last_error`.

## Reglas para modificar el proyecto

### Antes de editar

- Ejecuta `git status --short`; el árbol puede contener cambios del usuario o de otros agentes. No limpies ni reviertas cambios ajenos.
- Lee los archivos de la capa afectada y sus pruebas. No confíes solo en README o documentación.
- Comprueba el OpenAPI real en `/api/openapi.json` cuando cambies rutas.
- Mantén el proyecto local-first y los contenedores propios.

### Backend y datos

- Toda modificación del esquema requiere una nueva revisión Alembic; no edites migraciones ya aplicadas para simular una nueva versión.
- Mantén alineados modelo SQLAlchemy, esquema Pydantic, serialización de ruta, migración, seed y tipos del frontend.
- Usa la sesión inyectada por `get_db`; agrega el evento `record(...)` en la misma transacción para mutaciones relevantes.
- Valida antes de mutar y confirma con `db.commit()` una sola unidad lógica. En DCP, no elimines el snapshot ni la revalidación de confirmación.
- Conserva `Player.deleted.is_(False)` en consultas de inventario disponible.
- Si agregas un requisito DCP, impleméntalo tanto en `solve` como en `validate_solution` y añade pruebas factibles e imposibles.
- Un plan de emulador debe nacer de una solución revalidada, rechazar IDs repetidos/no disponibles/protegidos y guardar un snapshot inmutable de nombres y requisitos usados para construir sus pasos.
- Revalida de nuevo al preparar y al ejecutar. Conserva la resolución de calibración en el snapshot, compárala con `adb shell wm size` antes de encolar y al iniciar la tarea, y no permitas dos planes `queued`/`running` sobre el mismo serial.
- `AppSetting.value` es JSON mutable: conserva las copias `dict(...)` al leer/guardar la configuración de emulador o asigna un objeto nuevo, para que SQLAlchemy detecte y persista la calibración.
- Conserva las validaciones de dirección/serial ADB, coordenadas dentro de la pantalla, texto saneado, teclas permitidas, timeout y tamaño PNG. No expongas una ruta genérica para ejecutar comandos ADB arbitrarios.
- `build_dcp_steps` no debe generar etiquetas ni coordenadas de enviar/entregar; cualquier extensión requiere una prueba que demuestre que sigue deteniéndose antes del submit final.
- Las rutas de `InventoryScan` no deben persistir PNG/texto OCR completo. Conserva el rechazo de capturas repetidas, los topes, las frases diferenciadas y la selección explícita de jugadores.
- Los coeficientes efectivos del optimizador están codificados en `_cost`; el registro `app_settings.optimizer` aún es informativo y no reconfigura el solver. No documentes lo contrario sin conectar ambas capas.
- Los endpoints no llevan `/api` en `routes.py`. Nginx añade ese prefijo externamente y FastAPI usa `root_path="/api"`; `TestClient` llama rutas como `/health` y `/players`.

### Frontend

- La SPA no usa router de URL; `App.tsx` conserva la página seleccionada en estado local.
- Usa `api()` para JSON y conserva `FormData` sin forzar `Content-Type`.
- Tras una mutación, invalida todas las claves TanStack Query afectadas (`players`, `dashboard`, `duplicates`, `squads`, `challenges`, etc.).
- Actualiza `frontend/src/types/index.ts` cuando cambie una respuesta y mantén validación Zod/Pydantic coherente.
- Conserva navegación y controles utilizables en ancho móvil; el E2E usa emulación iPhone 13.
- El tema sí se persiste en `localStorage`; los datos del dominio pertenecen a PostgreSQL.
- La pantalla activa `CompanionPage` consulta estado/lecturas cada 5 s y planes cada 2,5 s; conserva estas actualizaciones o proporciona un reemplazo explícito para reflejar progreso/cancelación.

### Docker, secretos y archivos

- Añade valores configurables a `.env.example`, nunca credenciales reales ni `.env`.
- No confirmes dumps, inventarios reales, capturas, modelos de Ollama, `node_modules`, `dist` o la base SQLite de pruebas.
- Si cambias health checks o dependencias, valida un arranque desde servicios detenidos y la degradación sin Ollama.
- Si cambias ADB, valida primero la degradación sin dispositivo. Las pruebas con un dispositivo real deben usar datos desechables, una sesión iniciada manualmente y una pantalla sin acciones irreversibles al alcance de coordenadas no verificadas.
- Conserva los respaldos dentro de `backups/`; `restore.ps1` valida esa ruta, exige `.dump` y crea un dump previo.

## Pruebas según el cambio

Suite registrada en este estado: **30 Pytest, 2 Vitest y 2 Playwright**.

| Cambio | Verificación mínima |
| --- | --- |
| Documentación/configuración no ejecutable | Revisar enlaces/rutas y `docker compose config --quiet` si toca Compose |
| Servicio o endpoint backend | Pytest completo; health y OpenAPI del stack |
| Modelo o migración | Pytest, `alembic upgrade head`, `alembic current` y `alembic check` con PostgreSQL |
| Optimizador/requisitos | `test_optimizer.py` más un caso imposible y uno válido; confirmar que simular no muta |
| ADB/planes/calibración | `test_emulator.py`, OpenAPI y degradación sin dispositivo; con hardware, inspección manual y comprobación de que no existe submit final |
| Lectura de inventario/requisitos | Pytest de escaneo/revisión/importación y extractores; con hardware, contraste manual contra cartas visibles |
| Frontend o tipos | Vitest y `npm run build` mediante imagen/servicio |
| Navegación/layout/PWA | 2 casos Playwright iPhone y revisión manual a ~390 px, incluida la pantalla Emulador |
| Nginx/Docker | `docker compose config --quiet`, reconstrucción, `docker compose ps` y checks HTTP externos |
| Backup/restore | Probar con datos desechables y confirmar la copia previa; nunca usar primero datos únicos |

Antes de entregar un cambio de aplicación, ejecuta el conjunto más amplio razonable. Informa exactamente qué se ejecutó y cualquier prueba omitida.

## Criterio de finalización

Un cambio está terminado cuando código, migraciones, contratos, tipos, documentación y pruebas relevantes concuerdan; el stack conserva sus health checks; no se degradan las confirmaciones ni protecciones; y el estado del árbol se reporta sin atribuirse cambios ajenos.
