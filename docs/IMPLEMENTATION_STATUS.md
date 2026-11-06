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

## Escenarios de aceptación

- A: NO_EJECUTADA con sesión EA real. Recorrido sintético de 12 cartas y dos correcciones cubre transporte, OCR y revisión; no acredita 20 cartas reales.
- B/C/D: NO_EJECUTADA la nueva combinación de DCP reales, precios y compras. Los módulos heredados no equivalen a la funcionalidad pedida.
- E: nuevo escaneo/revisión funciona sin proveedor ni Ollama; cesta óptima pendiente.
- F: privacidad/cancelación ejercitadas con pantallas sintéticas y cancelación durante OCR; no hubo navegación sobre una cuenta EA.
