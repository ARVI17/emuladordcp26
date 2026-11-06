# Estado verificable · corte 5 de noviembre de 2026

Checkpoint del incremento visual. **No se ha completado el objetivo global de escaneo real + DCP + compras.** No se accedió a una sesión EA, no se instaló extensión ni se habilitó ningún proveedor externo. [Auditoría inicial](AUDIT_20261105.md).

| Etapa | Implementado/verificado | Pendiente |
| --- | --- | --- |
| 0 | Auditoría del checkout y de la instalación, rama separada desde FC27, dump y restauración en base aparte | Sin bloqueo de datos |
| 1 | Captura con gesto, máscaras/ROI, estabilidad, OCR cancelable, revisión paginada, commit idempotente y snapshots parciales | Validación con 20 cartas reales compartidas; reconocimiento de fichas gráficas/canónico y desambiguación asistida de copias entre páginas |
| 2 | La base previa conserva lectura manual de DCP y edición | Validar un tradicional y uno simplificado reales en el nuevo recorrido |
| 3 | Cotizaciones manuales previas y matriz de fuentes investigada | Importación normalizada y prueba completa de procedencia/plataforma/discrepancias |
| 4 | Solvers previos de inventario propio | Compras externas, presupuesto, coste de oportunidad, optimalidad/gap y prueba exhaustiva de mínimo |
| 5 | Vistas y planes previos preservados | Campo y lista exacta de compras integrados con el nuevo solver |
| 6 | Módulos previos de objetivos/Evos/IA preservados | Optimización conjunta sin doble gasto y escenarios de recomendaciones solicitados |
| 7 | Controles/pruebas del alcance nuevo y documentación | Rendimiento real, proveedor autorizado, actualización de Ollama fijada y revisión global al completar etapas |

## Evidencia durante el desarrollo

| Comando / informe en state/sprints | Resultado |
| --- | --- |
| `docker compose config --quiet` inicial | PASA |
| `docker compose run --rm --no-deps backend pytest -q` inicial | PASA: 36 en checkout antiguo; no confundir con FC27 |
| `python scripts/verify_docker.py --scope full` / 32a3f00ed7 | FALLA: pools Docker agotados después del build |
| `python scripts/verify_docker.py --scope backend --subnet 10.231.27.0/24` / 44e0cd66c4 | PASA: 306 Pytest, arranque, health/OpenAPI, migraciones; principal/volúmenes intactos |
| `python -m unittest discover -s scripts/tests -v` | PASA: 9 guardas del ciclo Docker |
| Full con `--pytest-path test_visual_scan.py --browser-spec visual-scan.spec.ts` / 7c890d04c1 | FALLA: una expectativa errónea de edición del seed; 10 casos nuevos pasaron. Corregida |
| Mismo comando / b0f370f4dd | 11 Pytest y Vitest PASA; Playwright FALLA por origen interno HTTP no confiable. Corregido solo en arnés |

Los resultados definitivos se añaden al cerrar la validación. No se cuentan intentos fallidos como pases ni se atribuye a una suite focalizada la cobertura integral.

Iteraciones siguientes: `13c565507f` detectó una confusión OCR entre «l» e «i» en un nombre sintético no lingüístico (12 casos pasaron); se conserva la revisión obligatoria y se usa una lista legible para el recorrido determinista. `361eb65085`: **13 Pytest y 42 Vitest PASA**, navegador todavía FALLA por origen HTTP. `457b5715da`: dos permisos denegados PASA, flujo de canvas FALLA por no emitir fotogramas nuevos. Se corrigieron el proxy loopback y el emisor sintético; no se rebajaron las protecciones de producción.

`python scripts/verify_docker.py --scope frontend --subnet 10.231.27.0/24 --browser-spec visual-scan.spec.ts` / **c9ba4b416b**: **PASA** build, arranque, health/OpenAPI, Alembic current/check, 42 Vitest y 3 Playwright (1 omitido: captura de canvas en móvil). Incluye Tesseract real y commit de 12 cartas corregidas; principal y volúmenes intactos. El respaldo restaurado fue comparado por recuento y hash de filas de **44 tablas**, idénticas al original.

## Validación integral y compatibilidad

`python scripts/verify_docker.py --scope full --subnet 10.231.27.0/24 --build-environment local` / **d280def9ff**, SHA `1b5c1ff`: **319 Pytest y 42 Vitest PASA**, build/arranque/health/OpenAPI/Alembic PASA; **37 Playwright PASA, 2 FALLA, 1 omitido**. Los dos fallos correspondían a la misma expectativa de texto antiguo de la guía de cuenta. Se actualizó la expectativa para comprobar el aviso nuevo que conserva la cuenta como no vinculada. La extensión no se ejecutó porque el verificador se detuvo en Playwright.

La revisión final añade compatibilidad SQLite mediante `batch_alter_table`, instala OCR/fuentes en CI y limita el proxy del test al entorno Docker. SQLite limpio: upgrade a 0021, current y check **PASA**. Se repitió una restauración del dump en `fc26_verify_visual_final_20261105`, se comprobó la imagen antigua `ea27c61`/0019 y luego la imagen nueva `8a80860`/0021 con bootstrap: **43 tablas de datos anteriores idénticas por hash y recuento**, más alembic_version actualizado; nuevas tablas reader_workflows/visual_snapshots. El primer ensayo de copia falló antes de conectar por una URL vacía en la configuración auxiliar; se corrigió usando las variables POSTGRES existentes, sin modificar datos.

`python -m unittest discover -s scripts/tests -v`: **9 PASA**. Revisión automatizada de enlaces Markdown: **140 rutas locales válidas**. `git diff --cached --check`: **PASA**. OpenAPI real: ocho rutas visuales, cuerpo binario PNG/JPEG/WebP y contrato ScanCommit presentes. Revisión visual de capturas sintéticas a 390 y 1280 px: controles legibles, flujo vertical móvil y sin desbordamiento horizontal. Ninguna de estas comprobaciones acredita precisión EA.

La repetición integral **dc69595a37** del commit limpio `8a80860` **PASA**: **319 Pytest, 42 Vitest, 39 Playwright y 14 pruebas de extensión**. Una prueba de canvas se omite intencionadamente en móvil; permiso denegado/layout sí pasan en ambos tamaños. Build, arranque sin Ollama, health/OpenAPI, Alembic 0021/current/check y limpieza pasan; principal y volúmenes permanecieron intactos. Imágenes marcadas `local`, SHA igual en frontend/API, árbol limpio al compilar.

CI de `8a80860` pasó frontend/extensión y 318 Pytest, pero falló una expectativa temporal: la primera petición tardó más de un segundo y la siguiente se aceptó correctamente. `d3838e7`/`855fd0f` corrigen solo el test: reloj y comienzo de ventana controlados, rechazo antes de un segundo y aceptación después. No cambia código de aplicación ni límites. La comprobación `git diff --exit-code 8a80860 HEAD -- backend/app backend/alembic frontend/src frontend/public backend/requirements.txt frontend/package.json frontend/package-lock.json docker-compose.yml nginx` confirmó igualdad del código desplegable.

`python scripts/verify_docker.py --scope backend --subnet 10.231.27.0/24 --pytest-path test_visual_scan.py` / **6a377aee90**: **13 PASA** después de la corrección temporal, junto con build, arranque, health/OpenAPI, current/check y limpieza. Los únicos cambios sin confirmar de esa ejecución eran documentación. Las imágenes personales se toman del pase integral limpio 8a80860, no de esa construcción focalizada.

CI posterior detectó también que el recorrido heredado `analyze-club.spec.ts` esperaba solo cinco segundos tras reanudar un cálculo. El artefacto mostraba la petición aún pendiente y botones deshabilitados, sin error de aplicación. La prueba ahora espera la respuesta HTTP dentro de 30 s, comprueba status active y la UI, con 60 s para el recorrido completo. `python scripts/verify_docker.py --scope frontend --subnet 10.231.27.0/24 --browser-spec analyze-club.spec.ts` / **42cbb3ebe2**: **42 Vitest y 2 Playwright PASA**, build, arranque, health/OpenAPI, current/check y limpieza también. La instalación personal y los volúmenes permanecieron intactos. La corrección es exclusiva del test; no cambia el análisis ni la aplicación desplegada.

El estado definitivo de CI de la rama se consulta en los [checks de la PR #8](https://github.com/ARVI17/emuladordcp26/pull/8/checks). Los fallos anteriores quedan registrados; un pase local o de un SHA anterior no se presenta como pase del último job remoto.

## Instalación local verificada

**http://localhost:8090**, frontend/API **8a808605d27dabc43266fdc4feeb739789708e5f**, entorno local, `source_dirty=false`; esquema **0021**. Cinco servicios saludables. Antes de abrir Nginx se compararon hashes/recuentos de todas las columnas anteriores: las **43 tablas de datos conservadas**, alembic_version actualizado, dos tablas nuevas vacías. Recuento posterior: **132 jugadores, 0 activos**. No se cargaron fixtures ni cartas de prueba en la base personal.

Comandos locales adicionales, todos PASA:

- `docker compose config --quiet`, variante `-f docker-compose.yml -f docker-compose.gpu.yml` y `-f docker-compose.review.yml`.
- `python state/visual-scan-release/prepare_release.py state/sprints/emuladordcp26-check-dc69595a37`: fija los IDs exactos de imágenes; no reconstruye.
- `docker compose --env-file state/visual-scan-release/empty.env -p emuladordcp26 -f state/visual-scan-release/release.compose.json config --quiet`.
- Misma composición: `up -d --no-deps --no-build --pull never --wait --wait-timeout 120 backend frontend`; luego `python state/visual-scan-release/integrity.py fc26`, `docker exec emuladordcp26-backend alembic current` y `alembic check`; luego `up -d --no-deps --no-build --pull never --wait --wait-timeout 90 nginx`.
- `docker start emuladordcp26-ollama`: conserva contenedor, imagen y volumen previos. No se ejecutó inferencia ni se cambió GPU/WSL.
- GET `/`, `/health`, `/api/openapi.json`, `/api/build`, `/build.json`: HTTP 200. SHA idéntico. Ocho rutas nuevas presentes; cabeceras CSP/nosniff/SAMEORIGIN/Referrer-Policy presentes. OPTIONS desde localhost:8090 permitido y desde origen ajeno rechazado con 400.
- `powershell -ExecutionPolicy Bypass -File scripts/fc27.ps1 Estado`: acredita URL única, cinco servicios saludables y versiones de imágenes.

La publicación fue exclusivamente local. .env, volúmenes, otros proyectos y worktrees se conservaron; PostgreSQL quedó limitado a 127.0.0.1:54326. Evidencia privada y composiciones de recuperación en `state/visual-scan-release/`; dump en `backups/visual-scan-before-20261105.dump`.

## Escenarios de aceptación pendientes del propietario

- A: NO_EJECUTADA con sesión EA real. Recorrido sintético de 12 cartas y dos correcciones cubre transporte, OCR y revisión; no acredita 20 cartas reales.
- B/C/D: NO_EJECUTADA la nueva combinación de DCP reales, precios y compras. Los módulos heredados no equivalen a la funcionalidad pedida.
- E: nuevo escaneo/revisión funciona sin proveedor ni Ollama; cesta óptima pendiente.
- F: privacidad/cancelación ejercitadas con pantallas sintéticas y cancelación durante OCR; no hubo navegación sobre una cuenta EA.
