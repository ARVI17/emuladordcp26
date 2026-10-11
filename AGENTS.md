# Guía persistente para agentes Codex

Este archivo es la entrada rápida para cualquier agente que trabaje en `emuladordcp26`. Lee también [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md) antes de cambiar arquitectura, datos o contratos HTTP.


## Estado del planificador (11 de octubre de 2026)

Lee [docs/FC27_PLANNER.md](docs/FC27_PLANNER.md) junto con el mapa. La entrada exige sesion/contexto y vigencia por dependencia; sin proveedor EA autorizado muestra **Integracion pendiente**. El modo local se elige expresamente. Reservas persistentes y aprobaciones no se pueden eludir desde rutas antiguas. Nunca habilites un proveedor ficticio ni una carga publica de snapshots verificados.

Head `0010` (tacticas privadas de plantilla): `0006` reconoce las dos variantes historicas de `0005` sin editarlas. El contexto 1 conserva registros sin vincular, nunca asignados a la primera cuenta. Las tablas personales usan ClubScoped; las mutaciones privadas requieren CSRF/entrada vigente. Restaurar exige local_simulation. Pulsaciones ADB deshabilitadas por falta de permiso aplicable; solo las pruebas mock sustituyen esa dependencia.

Revision: `docker-compose.review.yml`, loopback 8081, base tmpfs desechable. No contiene datos reales ni sustituye el stack normal. Resultados actuales en [docs/TESTING.md](docs/TESTING.md); cifras anteriores corresponden a PR #2.

## Flujo permanente por sprints

Trabaja con un agente y 1–3 objetivos funcionales por sprint. Antes de editar revisa Git, ramas/PR, este archivo y el mapa. Conserva cambios ajenos. Después de cada sprint con código: pruebas relevantes y Docker aislado, `git diff --check`, revisión de secretos, commit, push a la rama de trabajo y comparación del SHA remoto. Actualiza la PR en borrador, sin fusionar ni desplegar el stack principal. Un fallo pendiente se informa como WIP, nunca como prueba aprobada.

Usa `python scripts/verify_docker.py --scope full` para PostgreSQL, migraciones, HTTP, build, Vitest y Playwright con Nginx. Los scopes `backend` y `frontend` reducen únicamente las suites que no corresponden al cambio. El comando crea su propio proyecto y elimina solo sus contenedores al terminar, sin borrar volúmenes. Nunca ejecutes Pytest destructivo contra la base habitual.

`state/ENTORNO_LOCAL.md` y `state/sprints/` contienen evidencia privada ignorada; `.env`, dumps, logs, sesiones e inventarios reales no se publican. Conserva nombres y volúmenes principales. Migrar la instancia real exige respaldo restaurado en entorno separado, autorización específica y recuperación documentada. Las reglas del repositorio no conceden permisos nuevos. Consulta [docs/DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md).

## Propósito y estado real

`emuladordcp26` (Club Lab FC27) es una aplicación local y no oficial para administrar inventario revisado por edición, analizar jugadores, recomendar plantillas, mantener Galería histórica, simular evoluciones por caminos, actualizar contenido revisable, gestionar objetivos y simular/confirmar/restaurar DCP tradicionales o por puntos. Conserva el motor ADB, deshabilitado en producción por falta de permiso aplicable. La solución usa una SPA React, una API FastAPI, PostgreSQL, OR-Tools, un puente ADB y un chat opcional con Ollama, todo orquestado con Docker Compose.

El backend sí incluye el cliente ADB y puede conectar por TCP con un teléfono o emulador Android iniciado por el usuario, capturar/inspeccionar su pantalla, proponer inventario/requisitos, conservar planes revisables. Las rutas de toques, deslizamientos y ejecución rechazan acciones en producción. No instala ni inicia el emulador en el host, no se conecta a una API autenticada de EA y nunca automatiza el botón final de entrega, compras, ventas, inicio de sesión ni credenciales. En el entorno actual no hay ningún dispositivo/emulador conectado.

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

Compose limita RAM por servicio. La GPU NVIDIA es opcional y se activa con `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d`. El modelo se descarga tras el periodo equilibrado de `OLLAMA_KEEP_ALIVE`; verifica la aceleración después de una consulta con `docker compose exec ollama ollama ps`. Los límites se pueden ajustar mediante las variables `*_MEMORY_LIMIT` de `.env.example` sin editar Compose.

La configuración WSL2/Android depende del equipo del usuario; no supongas límites de RAM ni GPU disponibles. Los cambios persistentes de resolución/densidad/paquetes Android solo se aplican cuando se solicita `-OptimizeDevice`.

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

El entrypoint ejecuta `alembic upgrade head`, `app.db.bootstrap` y Uvicorn. Por defecto `SEED_DEMO=false`: bootstrap crea perfil vacío y clave privada HMAC. La demo explícita solo se carga antes del primer perfil. La migración `0005` conserva datos anteriores como FC26 y activa FC27; no renombres volúmenes para cambiar de edición.

## Mapa de código

- `docker-compose.yml`: servicios, health checks, variables, montajes y recursos dedicados.
- `nginx/nginx.conf`: proxy público, límite de carga y cabeceras de seguridad.
- `backend/app/main.py`: creación de FastAPI, CORS y manejadores globales de error.
- `backend/app/api/routes.py`: rutas generales y orquestación de sus transacciones.
- `backend/app/api/analysis.py`, `api/fc27.py`: análisis, Galería, evoluciones y contenido.
- `backend/app/services/locks.py`: reservas de inventario/dispositivo y bloqueo asesor PostgreSQL.
- `backend/app/api/emulator.py`: estado/conexión ADB, captura/OCR, lectura de inventario/requisitos, toques, calibración y ciclo de planes.
- `backend/app/models/entities.py`: entidades multiedición, Galería, evoluciones, propiedad de consumo, `AutomationPlan` e `InventoryScan`.
- `backend/app/schemas/api.py`: entradas Pydantic y sus límites.
- `backend/app/optimizers/sbc.py`: modelo CP-SAT, función de coste y validación final de DCP.
- `backend/app/services/rating.py`: aproximaciones de media.
- `backend/app/services/import_export.py`: CSV/XLSX y OCR en memoria.
- `backend/app/services/ollama.py`: estado y generación con degradación segura.
- `backend/app/services/adb.py`: ejecución ADB validada, captura, entrada permitida y generación/ejecución de pasos DCP.
- `backend/app/services/audit.py`: creación de eventos de auditoría dentro de la transacción llamante.
- `backend/app/db/session.py`: engine y sesiones.
- `backend/app/db/seed.py`: demo idempotente.
- `backend/alembic/versions/`: esquema reproducible; head actual `0009` (`trade_edition_market`).
- `frontend/src/App.tsx`: navegación/edición; vistas en `pages/`, componentes en `components/` y utilidades en `lib/`.
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

### FC27, identidad y consumos

- `Profile.game_version` es la edición activa. No conviertas datos FC26 en FC27 por cambiar el texto de la UI; toda mutación valida edición.
- Las reservas `resource_locks` y la recarga dentro de la reserva son obligatorias para mutaciones de inventario. Las garantías entre procesos requieren PostgreSQL.
- La protección efectiva une candado manual y pertenencia a cualquier equipo protegido. Desproteger un equipo no modifica `Player.protected`.
- Cada consumo tiene propietario `consumed_by_submission_id`. Restaurar valida todos los propietarios antes de tocar cartas; un snapshot ambiguo se rechaza.
- Galería es historial local: no elimina adquisiciones al consumir cartas, ignora cesiones y utiliza la carta base de evoluciones. Nunca inventar puntos/umbrales ni recompensas de EA.
- Las evoluciones son simulaciones sobre copia y exigen requisitos revisados. Los topes no deben reducir atributos/roles ya superiores.
- Paquetes de contenido requieren vista previa/hash, validación y recibo por hash. Noticias públicas no alteran requisitos automáticamente.
- Pruebas destructivas de tablas usan exclusivamente `TEST_DATABASE_URL` apuntando a datos desechables; nunca heredes `DATABASE_URL` de una instalación habitual.

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

Consulta `docs/TESTING.md` y CI para resultados de la revisión actual. La suite FC27 amplía backend, importaciones, Galería/evoluciones, protección, concurrencia y flujos frontend; distingue pruebas SQLite, PostgreSQL, navegador y hardware.

| Cambio | Verificación mínima |
| --- | --- |
| Documentación/configuración no ejecutable | Revisar enlaces/rutas y `docker compose config --quiet` si toca Compose |
| Servicio o endpoint backend | Pytest completo; health y OpenAPI del stack |
| Modelo o migración | Pytest, `alembic upgrade head`, `alembic current` y `alembic check` con PostgreSQL |
| Optimizador/requisitos | `test_optimizer.py` más un caso imposible y uno válido; confirmar que simular no muta |
| ADB/planes/calibración | `test_emulator.py`, OpenAPI y degradación sin dispositivo; con hardware, inspección manual y comprobación de que no existe submit final |
| Lectura de inventario/requisitos | Pytest de escaneo/revisión/importación y extractores; con hardware, contraste manual contra cartas visibles |
| Frontend o tipos | Vitest y `npm run build` mediante imagen/servicio |
| Navegación/layout/PWA | Suite Playwright iPhone y revisión manual a ~390 px, incluidas Galería/Análisis/Emulador |
| Nginx/Docker | `docker compose config --quiet`, reconstrucción, `docker compose ps` y checks HTTP externos |
| Backup/restore | Probar con datos desechables y confirmar la copia previa; nunca usar primero datos únicos |

Antes de entregar un cambio de aplicación, ejecuta el conjunto más amplio razonable. Informa exactamente qué se ejecutó y cualquier prueba omitida.

## Criterio de finalización

Un cambio está terminado cuando código, migraciones, contratos, tipos, documentación y pruebas relevantes concuerdan; el stack conserva sus health checks; no se degradan las confirmaciones ni protecciones; y el estado del árbol se reporta sin atribuirse cambios ajenos.
