# Pruebas del planificador FC27

## Lector estructurado, Galería v2 y diario (18-oct-2026)

La ampliación se valida con `scripts/verify_docker.py`: Compose temporal, PostgreSQL separados para API/pruebas destructivas, Nginx, build de SPA y extensión MV3 real en Chromium aislado. `/api/openapi.json` contiene las rutas nuevas de lector, cesta, plantillas DCP y diario. Alembic upgrade/current/check llega a **0018**. Principal y volúmenes permanecen sin cambios; se retiran únicamente contenedores/redes temporales propios.

El pase `7425f9a44a` superó **15 Pytest nuevos**, **38 Vitest**, **2 recorridos nuevos de móvil/escritorio** y **2 pruebas de extensión compilada**, además de build/salud/migraciones. El pase anterior de backend integral `ff32349a97` había superado **293 Pytest** (375,19 s); su navegador detectó la regresión UUID del diario en HTTP interno, corregida usando `getRandomValues`. El siguiente ensayo `b22bd85c7a` pasó los **30 recorridos preexistentes** y falló solo los dos nuevos por localizadores de selectores; se corrigieron sin quitar aserciones. Un fixture de cotizaciones incompleto también se corrigió antes del pase de 15. Los intentos fallidos no cuentan como pases integrales.

Casos nuevos: revisión por lote sin catálogo ficticio, recibo estable tras 20 reenvíos y después de revisar, colisión de evento, secuencias/edad/contexto/Host/Origin/CSRF, caducidad/revocación, ambigüedad de copias, FC26 y contenido sensible; propuestas calculadas con las cartas admitidas. Chromium simula pérdida del acuse y caída del transporte, termina el worker por CDP sin DevTools abiertos y recupera la cola al reanudar. No se reinicia Docker dentro de ese caso: la caída se simula en el proxy de pruebas.

Galería prueba subtotal porcentual 20, piso/tramos, primer propietario desconocido, multiplicidad, nivel holográfico sintético, base Evo, v1 conservada y premios marginales 35. Modelo y comprobador coinciden. La cesta compartida distingue compras/capital/neto/realizado, no recompra historia conocida, rechaza mercado/precio viejo y no crea propiedad. DCP conserva fijas y protegidas al sustituir, rechaza versiones de requisitos cambiadas y exceso de fijadas. El diario repite/corrige sin doble partido ni progreso EA, respetando modalidad/dificultad y edición.

Métricas del recorrido sintético compilado `7425f9a44a`: dos lecturas, 7.594 ms para la secuencia medida, 200.227 bytes de cuerpos de solicitudes del proxy (incluye reenvíos; no cabeceras), 24 recibos HTTP para dos eventos únicos; primer envío 144 ms, reenvíos entre 38 y 94 ms. Primera página: 99 campos presentes y 88 nulos, excluyendo ordinal/evidencia; no es una tasa de exactitud real. Heap JavaScript del panel: 6.109.756 bytes, no RAM total de Chrome. Cero solicitudes HTTP del recorrido a LLM/OCR y cero solicitudes públicas del navegador. Una muestra puntual del backend fue 301,1 MiB y PostgreSQL 103,7 MiB; no representa un pico ni un presupuesto de producción.

También pasaron ocho pruebas de guardas Docker, `docker compose config --quiet`, TypeScript/build de extensión y `npm audit --audit-level=high` (cero vulnerabilidades). Las capturas sintéticas se revisaron a ancho móvil; no hubo desbordamiento horizontal. Artefactos y métricas completos permanecen en `state/sprints/` y `frontend/test-results/`, ignorados por Git.

No se probaron lista/ficha/DCP reales de EA, cuenta autenticada, selector/permisos reales de EA, Safari/Android ni compras/ventas/entregas. Revocar la credencial local no equivale a una prueba de revocación del permiso de sitio mediante la UI de Chrome. El diagnóstico es mínimo, el extractor EA está pendiente y no hay recopilación autorizada nueva de FUT.GG. [Instalación, contratos y matriz](ASSISTED_READING.md).

## Lectura visual y aplicación manual guiada (12-oct-2026)

La captura es deliberada (`getDisplayMedia` sin audio o imagen adjunta), con OCR local, revisión y propiedad visual separada del catálogo/proveedor. El recorrido de navegador crea una imagen de texto sintético y la procesa con Tesseract real: cartas → revisión → principal protegida → objetivo revisado → solver → guía aprobada → resultado declarado → lectura posterior → conciliación idempotente. Se ejecutó en Chromium móvil y escritorio; las capturas sintéticas fueron revisadas y no hubo desbordamiento horizontal.

El pase integral `ee34a6c7bf` superó **278 Pytest/PostgreSQL, 38 Vitest y 30 Playwright**, compilación, arranque, health/OpenAPI y Alembic **0017**/check. Tras revisar la reapertura de una captura se añadió una regresión: un borrador de una sesión terminada puede releerse sin renovar ni duplicar evidencia revisada. El pase final `9fb6a5908f` superó **15 Pytest de lectura asistida, 38 Vitest y los 30 Playwright**, con build y migración correctos, tras incorporar esa regresión y los textos finales de interfaz. También pasaron **8 pruebas de guardas Docker** y `docker compose config --quiet`.

Los casos nuevos cubren rechazo de permiso, ilegibilidad/pantalla sensible/otra edición, nulos, páginas repetidas, copias ambiguas, cambio de contexto, caducidad, revisión concurrente, reservas, DCP sin protegidas, principal inmutable al guardar alternativas, cancelación/fallo con resultado desconocido y recibos repetidos sin doble registro. El OCR que confundía `EI` con `El` conserva el original y exige revisión; no acredita esa posición automáticamente.

Los primeros intentos descubrieron mutabilidad JSON en IDs revisados, consulta recursiva a un contexto expirado y un snapshot de Galería con fechas no serializables; se corrigieron. También se ajustaron selectores de navegador y la alternativa ante permiso denegado. Esos intentos fallidos no se cuentan como pases. Un aviso de deprecación compartido de Starlette/TestClient permanece.

Los verificados usaron proyectos Compose desechables, PostgreSQL propio y Nginx en loopback 8082. Se cerraron sus recursos y se conservaron IDs/arranques del principal y todos los volúmenes. La preparación de imágenes limpias y el ensayo de respaldo/migración/reinicio/recuperación guardan evidencia privada en `state/assisted-release/`; no despliegan 8080.

No se probó una captura del club personal, el selector del sistema operativo, Safari, autenticación remota ni escritura EA. La guía cubre preparación manual de una plantilla alternativa; DCP solo simula y Galería conserva historia local. El permiso del navegador se solicita de nuevo al compartir. [Uso y límites](ASSISTED_READING.md).

## Presupuesto conjunto y preparación de imágenes (12-oct-2026)

Las tres pruebas nuevas del conjunto verifican límite global, prioridad explícita, segmentos completos, exclusión de precios desconocidos bajo presupuesto, protección obligatoria y ausencia de consumo. Pasaron dentro del mismo ensayo final `0b98eba56f`: **264 Pytest, 34 Vitest y 28 Playwright**, con Nginx y PostgreSQL aislados. Los cambios del generador de objetivos y del presupuesto estaban presentes en esa imagen; se publican en commits separados por capa.

Las **8 pruebas de guardas Docker** pasaron. `fc27.ps1 Estado` muestra correctamente los acentos bajo Windows PowerShell y conservó la versión principal anterior. El nuevo argumento `--build-environment local` solo etiqueta las imágenes para preparar su publicación local; no relaja el aislamiento ni despliega. Se comprobará la revisión Git limpia antes de fijar imágenes para el ensayo de recuperación y la actualización autorizada.


## Plantillas para objetivos (12-oct-2026)

El generador usa reglas auxiliares revisadas y muestra por separado composición, contexto y acciones de partido. Las pruebas cubren mínimos/máximos/exactos, once/banquillo/convocatoria, metadatos desconocidos, modalidades incompatibles, dificultad, cesiones, titulares reutilizables y propuesta sin principal. Guardar/exportar conservan principal, copias y progreso; los comprobantes caducan o se invalidan al cambiar reglas, inventario, protecciones o progreso. Dos guardados concurrentes crean una sola alternativa; nombres repetidos se rechazan. Los contadores históricos sin evidencia siguen siendo desconocidos.

La primera migración nueva detectó columnas ya creadas por el modelo actual en la revisión histórica 0001; se corrigió únicamente 0016 para distinguir base nueva de instalación existente. Después pasaron 260 Pytest, y la ampliación final pasó 261. Dos recorridos de navegador señalaron selectores de prueba ambiguos (etiqueta de selector y dos encabezados de principal); se hicieron específicos, conservando las comprobaciones de exportación, guardado y estado idéntico antes/después. No se cuentan esos intentos como pases completos. Se revisaron las capturas sintéticas de la propuesta en móvil y escritorio.

La repetición final conjunta con el bloque de presupuesto pasó **264 Pytest/PostgreSQL** (285,33 s), **34 Vitest**, **28 Playwright** móvil/escritorio, build, salud/OpenAPI y Alembic **0016**/check. El informe `0b98eba56f` acredita cierre temporal y principal/volúmenes sin cambios. La lectura EA real, Safari y hardware siguen sin probar; una composición manual no acredita vigencia oficial ni progreso remoto. Los logs y capturas quedan en state/ ignorado, y las suites usan bases separadas de la instalación personal.

## Copias observadas y comparación con la principal (12-oct-2026)

La ejecución final aislada pasó **245 Pytest/PostgreSQL** (212,61 s), **33 Vitest**, **28 Playwright**, build, arranque, salud/OpenAPI y Alembic `0015`/check. Principal y volúmenes permanecieron sin cambios; los recursos temporales se retiraron. Los casos nuevos verifican 47 copias fuera del catálogo, paginación, variantes localizadas, dos copias y Evo individual, permanencia tras caducar el catálogo, bloqueo de lectura vencida, preferencias sin sustitución de hechos, metadatos nulos, filtro de ausencia e historial de Galería sin cesiones. La comparación por puesto no altera la principal.

La primera ejecución señaló dos expectativas que requerían actualización: editar una media observada ahora se rechaza en vez de invalidar el snapshot, y la prueba interna de Galería debe vincular su sesión al contexto observado. Tras corregirlas pasaron 245 pruebas. Una compilación posterior encontró dos errores de tipado en el nuevo fixture de interfaz; se completó su contrato y se corrigió el selector. La ejecución final pasó todas las capas.

El CI de la entrega anterior pasó en push y falló en un recorrido de PR: dos aperturas iniciales concurrentes de React en desarrollo podían cruzar cookie y CSRF. Se confirmó en el artefacto de error, se serializó `openEntry` y una prueba nueva verifica el orden completo de ambas aperturas. No se retiró la protección CSRF. La suite final también prueba la visibilidad de Mi club ante una lectura parcial y el formulario limitado a preferencias observadas.

No se probó un proveedor EA real, progreso remoto, hardware ADB ni GPU. Esta prueba del contrato interno no conecta la cuenta del propietario; tampoco actualiza por sí sola el puerto principal.

## Portada, navegación y cuenta observada (12-oct-2026)

**239 Pytest/PostgreSQL**, **30 Vitest**, build, Nginx, salud/OpenAPI y Alembic `0015`/check pasaron. La repetición final de frontend pasó **28 Playwright** en móvil y escritorio. Incluye Inicio sin saldos inventados, menú nativo, Atrás/Adelante/recarga, conservación de la entrada local explícita, foco, ayuda contextual, principal protegida y filtros. Se inspeccionaron las capturas reales de ambas portadas; no hubo desbordamientos.

Los casos nuevos comprueban cero frente a desconocido en FC Points, artículos de distintos tipos, procedencia/fecha inmutable al consultar el panel, lector sintético autorizado sin certificar progreso, filtros de rareza/valor, mensajes españoles e importación CSV/XLSX con separadores de miles. Las fechas usan Bogotá o la zona elegida y rechazan horas inexistentes por cambio de horario.

La primera ejecución pasó 237 Pytest y señaló expectativas anteriores de UI, soporte de diálogo ausente en jsdom y concurrencia de pruebas excesiva para el contenedor. Se actualizaron los contratos de prueba, se añadió el soporte del diálogo solo al arnés y se limitó Vitest a dos trabajadores. Un intento de build detectó una opción incorrecta en Testing Library; quedó corregida. La primera navegación de escritorio volvía atrás antes de terminar de abrir la página destino; el recorrido ahora espera esa vista, conserva la comprobación de foco y pasa en ambos tamaños. Cada intento cerró sus recursos y comprobó que principal y volúmenes permanecieron iguales.

No se probó vínculo EA real, Safari, GPU ni dispositivo ADB. El despliegue personal permanece separado de estas verificaciones; un resultado sintético no acredita acceso al club del propietario.

## Principal, filtros y operación única (12-oct-2026)

La verificación aislada con PostgreSQL pasó **224 Pytest** (190,02 s), build, salud, OpenAPI y Alembic `0015`/check. La repetición de frontend pasó **27 Vitest y 26 Playwright** sobre Nginx, incluidos móvil y escritorio para seleccionar principal, comprobar exclusiones, guardar filtros y duplicar sin alterar la principal. Se revisaron ambas capturas sintéticas. La primera suite detectó un recuento que incluía protecciones ocultas y un fixture sin principal revisada; se corrigieron. La nueva prueba de navegador esperaba la navegación antes de terminar la entrada local; ahora espera la confirmación visible de esa entrada. No se sustituyeron validadores por mocks.

Las pruebas nuevas cubren once/banquillo/reservas, rechazo en rutas directas, otra copia de la misma variante, propuesta para jugar con protegidos, cuarentena, ausencia de principal, comprobante de revisión y cambio concurrente bajo el bloqueo PostgreSQL. El fixture general selecciona una principal sintética; los casos de frontera conservan la falta de principal real. No hay conexión EA acreditada.

Operación: 8 pruebas de scripts, arranque canónico repetido desde dos directorios y ciclo Docker real tras éxito, fallo, cancelación y caída. La revisión personal anterior se preservó con un dump restaurado y comprobado antes de retirar sus cuatro contenedores. Las suites conservaron IDs/arranques del principal y todos los volúmenes; los entornos temporales se cerraron. Evidencia local en `state/single-app/` y `state/sprints/`, excluida de Git.

## Contenido y límites FC27 (sprint 9)

`python scripts/verify_docker.py --scope full` pasó en el proyecto desechable `bdacad27b7`: **212 Pytest/PostgreSQL** (157,03 s), **26 Vitest** y **24 Playwright** móvil/escritorio (aprox. 1 min). Build TypeScript/Vite/PWA, arranque, salud, OpenAPI y Alembic0014/check correctos. Se revisó la captura móvil de Novedades. El principal conservó contenedores/arranques; la limpieza temporal terminó sin borrar volúmenes.

Seis pruebas nuevas sin arnés de acreditación ejercitan prosa adversaria del modelo, historial no acreditado, noticias sin fecha/de otra edición/vencidas, formaciones distintas y caducadas, compatibilidad desconocida de Companion, 50 referencias sin posesión y caducidad de prácticas. El recorrido de navegador comprueba contenido pendiente, consulta FC27 y rechazo de otra edición. Las pruebas de puentes existentes solo simulan compatibilidad en una base desechable.

La primera ejecución completa detectó una prueba basada en el antiguo dibujo 4-3-3: 211 pases y un fallo. El caso de mediocampista polivalente se corrigió para usar 4-3-3 Holding. Una repetición iniciada antes de completar ese ajuste se detuvo y limpió; no se cuenta como pase. Después pasó el conjunto completo indicado arriba. La comprobación final `--scope backend`, proyecto `31192b8ab5`, volvió a pasar **212 pruebas** (158,92 s), build, arranque, salud, OpenAPI y Alembic/check tras cerrar ajustes internos, recuentos de reservas y respuestas caducadas. Frontend y navegador no se repitieron porque ese último ajuste solo afectó al backend. Se conserva un aviso de deprecación httpx/Starlette.

No se probó conexión EA, dispositivo real, Safari ni inferencia GPU/Ollama. La integración y compatibilidad siguen pendientes. No hubo migración de datos únicos, despliegue principal ni merge. El CI de `5bca18e` (sprint8) terminó correctamente en ambos eventos; los resultados del commit de este sprint se registran en su PR.

## Definiciones acreditadas (sprint 8)

Docker completo: **205 Pytest/PostgreSQL** (151,71 s), **26 Vitest**, **22 Playwright** y build/HTTP/OpenAPI/Alembic0014 correctos. Ocho pruebas de frontera omiten el arnés documental. El E2E repetido también envía un DCP sin evidencia y comprueba que solo aparece el aviso de pendientes. El arnés de navegador acredita definiciones exclusivamente con la cabecera explícita de preparación de fixtures; los formularios y casos de frontera siguen la admisión real.

Un intento previo pasó 203 casos y falló al escoger un perfil sintético sin ordenar en PostgreSQL. Se retiró la activación innecesaria del saldo demo en fixtures. Migración y restauración: 228 cartas, 228 entradas de Galería y cuatro planes conservados; dump0013 recuperado en una base distinta. El WAL y shared_buffers del PostgreSQL desechable se ajustaron dentro de512MB; principal intacto.

CI del sprint7 pasó backend y falló al arrancar Uvicorn porque no encontraba `app`; el workflow ahora declara `PYTHONPATH`. El estado remoto del siguiente commit debe comprobarse antes de afirmar pase de CI. El pase local Docker no sustituye esa comprobación.

## Estado vigente: catálogo y cuarentena (sprint 7)

Docker aislado: **197 Pytest/PostgreSQL** (122,67 s), **26 Vitest**, **22 Playwright** móvil/escritorio sobre Nginx (50,6 s), build, salud, OpenAPI y Alembic0013/check correctos. Las suites frontend se repitieron tras ajustar dos contratos antiguos de mensajes/variantes. El principal conservó IDs y arranques. El límite de PostgreSQL de pruebas pasó a512MB tras un OOM registrado; no se cambió el principal.

Migración poblada y recuperación:228cartas,228entradasGalería y4planes conservados; dump previo0012 restaurado en otra base. Cinco guardas del comando Docker correctas; revisión visual del catálogo móvil. No se probaron Safari, GPU/Ollama ni hardware/EA.

La preparación general emplea evidencia sintética únicamente en bases desechables. Seis pruebas `catalog_boundary` y el recorrido de cuarentena omiten la autocertificación de fixtures. El entrypoint E2E vigente es `PLAYWRIGHT_DISPOSABLE_DB=1 uvicorn --app-dir tests e2e_app:app`; el arranque normal `app.main` nunca admite ese arnés ni crea demo. Procedimiento actual: [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md). Los resultados y comandos multiedición siguientes son registro histórico; no habilitan un selector ni sustituyen este flujo.

## Flujo reproducible por sprints

Sprint 1, 11-oct-2026: `python scripts/verify_docker.py --scope full` pasó con **155 Pytest/PostgreSQL**, **25 Vitest**, **12 Playwright** sobre Nginx, build, migraciones/HTTP y limpieza del proyecto temporal. Cinco pruebas del comando rechazaron configuraciones peligrosas. El primer intento detectó una suposición fija de ADB en una prueba; se corrigió para comprobar activado/desactivado sin dispositivos y se repitió toda la ejecución. El stack principal conservó IDs y fechas de arranque. Procedimiento: [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md). Evidencia privada en `state/sprints/`.

Sprint 2: **167 Pytest/PostgreSQL** correctos, build, arranque, Alembic/HTTP y OpenAPI con 98 rutas. Se ejecutó `--scope backend`: Vitest/Playwright no se repitieron porque no cambió la interfaz. Lecturas, permisos, cuotas, cancelación y timeout se probaron exclusivamente con adaptadores sintéticos; cero acceso EA. El timeout real del ejecutor descarta también una respuesta que llega después del plazo. El comando retiró el stack temporal y verificó que el principal no se reinició.

Sprint 3: **171 Pytest/PostgreSQL, 25 Vitest y 14 Playwright** correctos mediante `--scope full`, build, salud y Alembic. Tras ajustar las etiquetas de química/disponibilidad se repitió `--scope frontend`: build, 25 Vitest y 14 Playwright correctos, con revisión visual móvil. Un dump desechable en `0009` se restauró y migró a `0010`, conservando 228 cartas, 228 entradas de Galería y cuatro planes. SQLite nuevo también pasó migración, `alembic check` y seed. Un arranque inicial detectó que la migración histórica crea columnas del modelo actual; se corrigió únicamente la nueva revisión `0010` y se repitieron las pruebas. Sin acceso EA, hardware ni despliegue principal.

Sprint 4: **175 Pytest/PostgreSQL** (97,14 s), **25 Vitest** y build correctos. El primer E2E detectó dos selectores ambiguos; corregidos, `--scope frontend` repitió build/Vitest y **16 Playwright** (34,7 s), incluida práctica, vínculo al diario y aislamiento FC26/FC27. Revisión visual móvil realizada. Dump0009 restaurado y migrado a0011: 228 cartas, 228 entradas de Galería, cuatro planes y un partido antiguo conservado sin edición inventada. SQLite upgrade/check correcto. EA, hardware y despliegue principal siguen pendientes.

Sprint 5: `--scope full` pasó con **182 Pytest/PostgreSQL** (103,39 s; un aviso httpx), **25 Vitest** y **20 Playwright** (41,6 s), build, salud, OpenAPI y Alembic. Tras traducir tipos de cotización y mostrar la hora observada se repitió `--scope frontend`: build/25 Vitest/20 Playwright (40,1 s) correctos. Revisadas capturas móviles de agenda y alertas. Cinco guardas del comando Docker correctas. El primer intento terminó con 175 pases y siete errores por OOM del PostgreSQL temporal de 256 MB mientras se restauraban dos bases adicionales; se separaron las cargas y la repetición completa pasó sin ampliar recursos ni tocar el principal.

Migración 0011→0012 sobre datos restaurados: 228 cartas, 228 entradas de Galería, cuatro planes y una práctica conservados; `alembic check` correcto. El dump previo0011 también se restauró y contrastó en otra base desechable. No se repitieron GPU/Ollama, hardware, Safari ni EA; ninguna instancia principal fue migrada.

## Registro de la implementación inicial



Ejecucion local del **11 de octubre de 2026**, worktree `agent/fc27-club-planner`. Datos exclusivamente desechables. El registro anterior de PR #2 se conserva mas abajo y no se atribuye a este cambio.

| Verificacion actual | Resultado |
| --- | --- |
| Pytest completo, PostgreSQL 16 aislado | **154 passed**, 1 aviso httpx/Starlette, 121,18 s; ninguno omitido |
| Vitest | **25 passed en 11 archivos** |
| TypeScript/Vite/PWA en imagen Docker | Build correcto |
| Playwright por Nginx/API/PostgreSQL reales | **12 passed**, 29,1 s, Chromium iPhone 13 y escritorio 1280 x 900 |
| Migraciones desde 0005 Companion y 0005 FC27 | Ambas a **0009**, alembic check sin cambios, conservadas 132 cartas FC26 y 132 FC27 respectivamente |
| Migracion de consumo/historial | Conserva 132 cartas, carta 1 eliminada logicamente, consumed_by_submission_id=1, entrega propietaria y Galeria |
| Dump/restauracion PostgreSQL desechable | pg_dump -Fc / pg_restore --exit-on-error: head 0009, 132 cartas restauradas |
| SQLite desechable del flujo CI | upgrade head 0009, alembic check y bootstrap correctos |
| Degradacion | Revision sin Ollama ni dispositivo ADB; modulos principales utilizables |
| Compose y stack de revisión | Configuraciones válidas, cuatro servicios healthy, head 0009 y alembic check sin cambios |
| HTTP y contratos | Health 200 en 8081 y en el original 8080; OpenAPI de revisión válido, 97 rutas |
| Proveedor EA / club del usuario / hardware | **No probados: acceso autorizado y dispositivo pendientes** |

Los E2E cubren entrada pendiente, modo local expreso, navegacion/layout, plantillas/Galeria, mercado, 50 referencias y reserva/cancelacion sin consumo. Solo el diagnostico ADB sustituye su estado; las mutaciones del planificador usan la API real. Capturas revisadas de entrada, plan y vistas heredadas. Artefactos locales en `frontend/test-results/`, sin versionar.

`test_planner.py` usa lecturas remotas **sinteticas**: relecturas/dos copias/movimientos, parcial, cuenta/logout/expiracion, rollback al fallar commit, preferencias, frescura por modulo y cuotas. Cubre reservas concurrentes de cartas/monedas, rutas antiguas, dos pasos/cambio externo, aprobacion caducada/alterada/repetida, perdida parcial, incertidumbre, variante/mercado/edicion/precio incorrectos, homonimos/calidad de atributos, disjuntos y catalogo/progreso separado. Una enumeracion independiente obtiene coste DCP conjunto 3 frente a 101 de elecciones separadas; timeout no afirma imposibilidad.

## Reproducir sin tocar datos normales

Pytest recrea tablas. Se uso exclusivamente `TEST_DATABASE_URL` con contenedor `emuladordcp26-planner-test-db`, red `emuladordcp26_planner_test`, base `planner_test`. Migraciones en otras bases `planner_migration_*`; dumps en `backups/`.

```powershell
# Requiere esa base exclusivamente desechable.
docker run --rm --network emuladordcp26_planner_test --mount "type=bind,source=$PWD/backend,target=/app" -e TEST_DATABASE_URL=postgresql+psycopg://planner_test:planner_test_only@emuladordcp26-planner-test-db:5432/planner_test --entrypoint python emuladordcp26-planner-backend -m pytest -q

docker compose -f docker-compose.review.yml up --build -d
docker compose -f docker-compose.review.yml exec backend alembic current
docker compose -f docker-compose.review.yml exec backend alembic check
docker compose -f docker-compose.review.yml build frontend-e2e
docker compose -f docker-compose.review.yml run --rm frontend-e2e
```

Build: `npm run build`. Vitest: `npm test -- --run` en imagen de build montando `frontend/src`. Revision en localhost:8081; el stack original localhost:8080 no se migro ni reconstruyo. No se probaron scripts PowerShell de restauracion, GPU/inferencia Ollama, Safari ni operaciones EA.

## Medicion acotada

`python -m benchmarks.planner` genera cartas solo en memoria. Con 512 MB, comparar diez formaciones equilibradas tardo **0,529 s para 132 copias** y **1,569 s para 1000**: diez onces completos, optimal en ambos casos. Excluye HTTP, proveedor, DB, otros estilos e inventarios. Objetivo de referencia: menos de cinco segundos para esa muestra de 1000 cartas; no es SLA ni una aceleracion porcentual sin linea base.

# Registro histórico de PR #2

Esta página distingue pruebas ejecutadas de verificaciones pendientes. La [CI del 10 de octubre de 2026 UTC](https://github.com/ARVI17/emuladordcp26/actions/runs/38020243563) terminó correctamente sobre el código [ba9c17b47c67ab4a9dadedd1de87d647db20496e](https://github.com/ARVI17/emuladordcp26/commit/ba9c17b47c67ab4a9dadedd1de87d647db20496e). Los resultados usan datos desechables; no describen una ejecución de producción ni garantizan comportamiento en un dispositivo Companion real.

## Estado registrado

| Comprobación | Resultado |
| --- | --- |
| Pytest local con dependencias actualizadas y SQLite aislada | **109 correctos, 2 casos PostgreSQL omitidos** |
| Pytest en PostgreSQL 16 de CI | **111 correctos**, incluidos los dos casos de bloqueo entre procesos; [job backend](https://github.com/ARVI17/emuladordcp26/actions/runs/38020243563/job/114119429998) |
| Migración PostgreSQL desde PR1 | Actualización a `0005`, conservación de **132 cartas FC26**, perfil FC27 y `alembic check` correctos |
| Vitest frontend | **24 correctos en 10 archivos**; [job frontend](https://github.com/ARVI17/emuladordcp26/actions/runs/38020243563/job/114119430117) |
| TypeScript, Vite y PWA | Build correcto en CI |
| Auditoría npm de producción | **0 vulnerabilidades reportadas** en esa ejecución; alcance y desarrollo en [SECURITY.md](SECURITY.md) |
| Playwright Chromium contra Vite y API real | **6/6 correctos**, viewport móvil de **390 × 664 px CSS** y escritorio de **1280 × 900 px**; pantalla móvil emulada de 390 × 844 px, DPR 3 |
| Revisión visual de plantillas y Galería | Cuatro capturas revisadas, móvil/escritorio, sin desbordamiento horizontal ni defectos materiales observados en esas vistas; [artefacto](https://github.com/ARVI17/emuladordcp26/actions/runs/38020243563/artifacts/11657254992) |
| Comprobación HTTP local complementaria | **26 comprobaciones correctas**, con 223 cartas ficticias |
| Compilación de módulos Python modificados | Correcta |
| Whitespace/diff de los cambios verificados | `git diff --check` correcto |
| Configuración Compose base y GPU | Ambas válidas en CI mediante `docker compose config --quiet` |
| Build y arranque del stack Docker completo, incluido Nginx | Pendientes |
| Backup/restauración PowerShell real, Safari y Companion FC27 con hardware o club EA real | Pendientes |

Pytest terminó con un aviso de deprecación por el uso de httpx en TestClient con la versión de Starlette instalada. El resultado PostgreSQL fue `111 passed, 1 warning`; la diferencia respecto a SQLite corresponde a los dos casos de integración que allí se omiten.

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

[.github/workflows/ci.yml](../.github/workflows/ci.yml) prepara PostgreSQL 16 en una base de CI desechable. El [job backend del 10 de octubre](https://github.com/ARVI17/emuladordcp26/actions/runs/38020243563/job/114119429998) ejecutó correctamente esta secuencia:

1. Crear una base con el código anterior de PR1 y cargar sus datos FC26.
2. Aplicar la migración actual, consultar `alembic current` y ejecutar `alembic check`.
3. Verificar que se conservan 132 jugadores FC26 y que el perfil selecciona FC27.
4. Ejecutar la suite con `TEST_DATABASE_URL` PostgreSQL, incluidos los dos casos entre procesos.
5. Validar las configuraciones Compose base y con GPU.

[test_postgres_integration.py](../backend/tests/test_postgres_integration.py) comprueba que una reserva asesora sigue vigente después de un commit y excluye a otro proceso. Cubre las claves `inventory` y dispositivo; después de liberar la reserva, otro proceso debe poder adquirirla. Estos casos se omiten expresamente cuando no se configura PostgreSQL de prueba.

El log confirma `0005 (head)`, `No new upgrade operations detected.` y `111 passed, 1 warning in 39.58s`. Los dos casos entre procesos se ejecutaron con PostgreSQL y pasaron. Las comprobaciones de Compose validan la configuración base y la variante GPU; no construyen ni arrancan todas las imágenes de la aplicación.

Para inspeccionar el estado de una instalación ya iniciada, sin ejecutar la suite destructiva contra ella:

```bash
docker compose exec backend alembic current
docker compose exec backend alembic check
```

Una migración limpia o un ensayo de actualización debe realizarse en una base o un respaldo restaurado de pruebas, separado del inventario real.

## Frontend

[frontend/package.json](../frontend/package.json) define Vitest, compilación y dependencias. El [job frontend](https://github.com/ARVI17/emuladordcp26/actions/runs/38020243563/job/114119430117) instaló con `npm ci`, superó 24 pruebas en 10 archivos y compiló TypeScript, Vite y PWA. Se puede repetir la parte de pruebas y build con:

```bash
cd frontend
npm test -- --run
npm run build
```

También se puede usar `docker compose run --rm frontend-test`. La auditoría `npm audit --omit=dev --audit-level=high` del job terminó con `found 0 vulnerabilities`. Ese resultado corresponde a las dependencias de producción de esta revisión y fecha; no afirma ausencia de avisos en el árbol de desarrollo. Consulte [SECURITY.md](SECURITY.md).

## E2E ejecutado y revisión manual pendiente

En la [CI verificada](https://github.com/ARVI17/emuladordcp26/actions/runs/38020243563/job/114119430117), Playwright ejecutó tres escenarios en Chromium para móvil y escritorio: **6/6 correctos en 11,8 segundos**. El perfil `iPhone 13` de Playwright 1.62.1 utiliza un **viewport de 390 × 664 píxeles CSS**, pantalla emulada de **390 × 844 píxeles** y DPR 3; el viewport de escritorio es **1280 × 900 píxeles**. Usó una API FastAPI real con SQLite desechable, ADB desactivado y Vite redirigiendo `/api` a Uvicorn. El build de producción se comprobó por separado; estos recorridos no atravesaron los contenedores ni el Nginx del despliegue Docker.

El recorrido FC27 crea once cartas propias a partir de las posiciones de `/squads/formations`, propone y guarda un equipo y registra su Galería. Requiere `PLAYWRIGHT_DISPOSABLE_DB=1` y una base exclusiva de pruebas; sin esa variable se omite ese recorrido con escrituras. Los otros dos escenarios no dependen de su orden. La emulación móvil Chromium no comprueba Safari ni un teléfono real.

El artefacto [fc27-browser-verification, ID 11657254992](https://github.com/ARVI17/emuladordcp26/actions/runs/38020243563/artifacts/11657254992) contiene las capturas de plantillas/Galería y el registro de API. Se revisaron las cuatro capturas, dos vistas en móvil y escritorio, sin desbordamiento horizontal ni defectos materiales observados. Esta revisión visual se limita a esas capturas; el pase de hardware sigue pendiente. El workflow establece una retención de siete días para ese artefacto.

El servicio Docker `frontend-e2e` permite probar contra Nginx mediante Playwright, pero esa variante aún no se ha ejecutado en esta verificación.

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

La descarga de Chromium estuvo bloqueada en el entorno local antes de abrir páginas; esa limitación local no impidió el pase posterior de los seis recorridos en CI. Las cuatro capturas revisadas son evidencia de esas pantallas y resoluciones, no de todos los flujos ni de Safari. El pase manual ampliado y la repetición sobre el stack Docker completo deben comprobar, con datos desechables:

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

Siguen pendientes el build/arranque del stack Docker completo, el E2E a través de su Nginx, backup/restauración reales mediante PowerShell, Safari y un teléfono/emulador con Companion y un club EA real. Esos resultados deben añadirse cuando se ejecuten, indicando versión de Companion, resolución, entorno y cualquier fallo observado. Los datos de las comprobaciones registradas son ficticios y no demuestran una sincronización ni una entrega real en EA.

## Frontera exclusivamente FC27

Docker aislado: 191 Pytest/PostgreSQL, 25 Vitest y 20 Playwright (móvil/escritorio), build, health, OpenAPI y Alembic correctos. Se incluyen perfiles históricos, relaciones mixtas y rechazo de rutas de archivo. Datos antiguos conservados; stack principal sin cambios. Dos ejecuciones previas detectaron contratos de pruebas obsoletos y un 500 al acceder a un segmento histórico; corregidos antes del pase completo.
