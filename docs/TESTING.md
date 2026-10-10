# Pruebas y estado de verificación

Esta página distingue pruebas ejecutadas de verificaciones preparadas. Los resultados corresponden a la actualización FC27 en desarrollo; no describen una ejecución de producción ni garantizan comportamiento en un dispositivo Companion real.

## Estado registrado

| Comprobación | Resultado |
| --- | --- |
| Pytest backend completo con dependencias actualizadas y SQLite aislada | **109 correctos, 2 omitidos** |
| Integración PostgreSQL entre procesos | Dos casos preparados; omitidos porque la ejecución local usa SQLite |
| Vitest frontend | **24 correctos en 10 archivos** |
| Compilación de módulos Python modificados | Correcta |
| Whitespace/diff de los cambios verificados | `git diff --check` correcto |
| Workflow CI de PostgreSQL 16, migraciones y frontend | Preparado; todavía no ejecutado para esta actualización |
| Playwright E2E y revisión visual FC27 | Seis recorridos preparados; ejecución local bloqueada por la descarga del navegador |
| Companion FC27 con teléfono/emulador real | Pendiente |

Pytest muestra un aviso de deprecación por el uso de httpx en TestClient con la versión de Starlette instalada. La suite terminó correctamente; el aviso no valida ni invalida los flujos de producción.

## Backend y aislamiento de datos

[conftest.py](../backend/tests/conftest.py) reconstruye las tablas y carga la demo por caso. Usa exclusivamente `TEST_DATABASE_URL`, con `sqlite+pysqlite:///./test_fc26.db` como valor predeterminado; el nombre histórico del archivo no cambia la edición de las pruebas. Ignora un `DATABASE_URL` general para impedir que una configuración habitual seleccione accidentalmente la base del usuario.

**La suite borra tablas de la base que indique `TEST_DATABASE_URL`. Esa variable debe apuntar siempre a datos desechables.** Para ejecuciones concurrentes, cada proceso o agente necesita un archivo o una base diferente.

Desde `backend`, con las dependencias de [requirements.txt](../backend/requirements.txt) instaladas:

```bash
TEST_DATABASE_URL=sqlite+pysqlite:////tmp/fc27-backend-test.db python -m pytest -q
```

Alternativa desde la raíz del proyecto:

```bash
docker compose run --rm --no-deps backend pytest -q
```

El entrypoint detecta el comando explícito y ejecuta pytest directamente. No necesita migrar la base habitual para arrancar esta suite SQLite.

### Qué comprueba

| Área | Casos relevantes | Fuente |
| --- | --- | --- |
| API y arranque | Health, demo, perfil/panel sin demo, CRUD, actualizaciones inválidas, objetivos, aislamiento por edición | [test_api.py](../backend/tests/test_api.py), [test_fc27.py](../backend/tests/test_fc27.py) |
| Selección DCP | Combinaciones válidas/imposibles, protegidos, duplicados, coherencia de media y validador | [test_optimizer.py](../backend/tests/test_optimizer.py), [test_rating.py](../backend/tests/test_rating.py) |
| Análisis | Cinco formaciones, posiciones alternativas, atributos, fijados/excluidos, identidad, huecos y cero escrituras | [test_squad_analysis.py](../backend/tests/test_squad_analysis.py) |
| Consumo/restauración | Doble confirmación concurrente, propietario único, validación completa antes de restaurar, protección manual/plantillas | [test_squad_analysis.py](../backend/tests/test_squad_analysis.py) |
| Puntos DCP | Entregas parciales, progreso derivado, restauración de un lote, presupuesto acumulado, rechazo de puntos desconocidos | [test_squad_analysis.py](../backend/tests/test_squad_analysis.py) |
| Galería y evoluciones | Historial, conciliación de versiones/puntos, datos revisados, reglas, ramas y proyecciones sin mutaciones | [test_fc27.py](../backend/tests/test_fc27.py) |
| Importación | Rango y tipo por fila, metadatos, fórmulas de hoja de cálculo, archivo/edición vinculados y repetición idempotente | [test_import_export_safety.py](../backend/tests/test_import_export_safety.py), [test_squad_analysis.py](../backend/tests/test_squad_analysis.py) |
| ADB y OCR | Degradación sin dispositivo, emparejamiento, revisión por candidatos, firmas, límites, planes, exclusión, cancelación y snapshots | [test_emulator.py](../backend/tests/test_emulator.py), [test_emulator_safety.py](../backend/tests/test_emulator_safety.py) |

Las pruebas que simulan un dispositivo comprueban contratos y decisiones del programa. No sustituyen la comprobación de OCR, coordenadas y resultados de búsqueda en una versión real de Companion.

## PostgreSQL, migraciones y CI

El head de Alembic es [0005](../backend/alembic/versions/0005_fc27_club.py). La migración añade metadatos/entidades FC27 y preserva los datos anteriores como FC26, incluyendo la asignación de propietario de consumo cuando existe uno inequívoco.

[.github/workflows/ci.yml](../.github/workflows/ci.yml) prepara PostgreSQL 16 en una base de CI desechable. El trabajo backend está configurado para:

1. Crear una base con el código anterior de PR1 y cargar sus datos FC26.
2. Aplicar la migración actual, consultar `alembic current` y ejecutar `alembic check`.
3. Verificar que se conservan 132 jugadores FC26 y que el perfil selecciona FC27.
4. Ejecutar la suite con `TEST_DATABASE_URL` PostgreSQL, incluidos los dos casos entre procesos.
5. Validar las configuraciones Compose base y con GPU.

[test_postgres_integration.py](../backend/tests/test_postgres_integration.py) comprueba que una reserva asesora sigue vigente después de un commit y excluye a otro proceso. Cubre las claves `inventory` y dispositivo; después de liberar la reserva, otro proceso debe poder adquirirla. Estos casos se omiten expresamente cuando no se configura PostgreSQL de prueba.

La definición del workflow no equivale a una ejecución correcta. En el estado registrado todavía falta su resultado real. Una prueba SQLite de dos peticiones concurrentes tampoco prueba por sí misma el bloqueo entre procesos de PostgreSQL.

Para inspeccionar el estado de una instalación ya iniciada, sin ejecutar la suite destructiva contra ella:

```bash
docker compose exec backend alembic current
docker compose exec backend alembic check
```

Una migración limpia o un ensayo de actualización debe realizarse en una base o un respaldo restaurado de pruebas, separado del inventario real.

## Frontend

[frontend/package.json](../frontend/package.json) define Vitest, compilación y dependencias. Los 24 casos registrados cubren contratos/formularios/utilidades del frontend actualizado. La compilación se verifica con TypeScript y Vite:

```bash
cd frontend
npm test -- --run
npm run build
```

También se puede usar `docker compose run --rm frontend-test`. El trabajo frontend de CI instala con `npm ci`, ejecuta pruebas y build, y consulta advisories de dependencias de producción. Ese trabajo sigue pendiente de ejecución remota en el estado de esta página.

## E2E y revisión manual pendiente

El servicio `frontend-e2e` prueba contra Nginx mediante Playwright. La configuración prepara tres escenarios en Chromium para móvil de 390 × 844 px y escritorio de 1280 × 900 px, con un solo trabajador. La emulación móvil no comprueba Safari ni un teléfono real. El recorrido FC27 crea once cartas propias a partir de las posiciones de `/squads/formations`, propone y guarda un equipo y registra su Galería. Requiere `PLAYWRIGHT_DISPOSABLE_DB=1` y una base exclusiva de pruebas; sin esa variable se omite ese recorrido con escrituras. Los otros dos escenarios no dependen de su orden.

Con un stack de pruebas accesible:

```bash
docker compose run --rm -e PLAYWRIGHT_DISPOSABLE_DB=1 frontend-e2e
```

Para CI o desarrollo sin Docker, inicia la API en `127.0.0.1:8000` con una SQLite desechable y la demo explícita. Desde `backend`, en una terminal con las dependencias instaladas:

```bash
export DATABASE_URL=sqlite:////tmp/fc27-e2e.db
export ADB_ENABLED=false
export SEED_DEMO=true
alembic upgrade head
python -m app.db.bootstrap
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

En otra terminal, desde la raíz, Playwright inicia Vite en el puerto 5173 y este redirige `/api` al puerto 8000:

```bash
cd frontend
npm ci
npx playwright install --with-deps chromium
PLAYWRIGHT_DISPOSABLE_DB=1 npm run test:e2e
```

Si Vite ya está iniciado, configura también `PLAYWRIGHT_BASE_URL=http://127.0.0.1:5173`; con una URL externa, Playwright no inicia su propio servidor. En entornos que aíslan la red de cada ejecución, API, Vite y las pruebas deben ser procesos de una misma ejecución permitida.

El resultado E2E de la actualización FC27 está pendiente. En la verificación local, las descargas oficiales de Chromium y de Headless Shell recibieron un HTML «Site Unavailable» en lugar del archivo del navegador. La ejecución quedó bloqueada antes de abrir páginas; no se ha validado visualmente el diseño ni se declara un pase de navegador. No se debe reutilizar como evidencia un resultado anterior a estos cambios. El pase manual debe comprobar, con datos desechables:

1. Arranque con `SEED_DEMO=false`, respuestas de `/health`, `/api/dashboard`, `/api/docs` y navegación en móvil.
2. Cambio FC26/FC27 conservando datos y cachés coherentes.
3. Importación con revisión; rechazo al cambiar archivo/edición y repetición sin duplicados.
4. Análisis con posiciones alternativas, fijados/excluidos, banquillo y huecos; guardar una recomendación.
5. Protección manual y por dos plantillas; rechazo del consumo mientras exista alguna protección.
6. Simulación tradicional sin cambios de inventario; confirmación local y restauración desde historial.
7. Dos lotes score, progreso parcial/completo y restauración de solo uno.
8. Galería antes y después de consumir una carta; puntos desconocidos y corrección de una versión.
9. Vista previa e importación de contenido; evolución válida, incompatible y con datos ausentes.
10. Temas y controles a aproximadamente 390 px, errores visibles, acciones en curso y prevención de confirmaciones dobles.

### Dispositivo ADB

Primero compruebe que `/api/emulator/status` degrada sin dispositivo y el resto de la aplicación sigue disponible. Con un dispositivo de prueba, revise pantalla/resolución, calibre, capture, corrija candidatos y confirme únicamente la importación local seleccionada.

Para un plan tradicional, compruebe frase incorrecta, cambios de carta/calibración, preparación, ejecución y cancelación. Inspeccione que ningún paso incluya la pulsación final de entrega. Los score deben rechazarse antes de generar preparación automática. La preparación puede cambiar la selección visible en el dispositivo; use datos y una pantalla que permitan revisar esos efectos.

Los resultados de hardware, stack Docker completo y E2E deben añadirse cuando se ejecuten, indicando versión de Companion, resolución, entorno y cualquier fallo observado.
