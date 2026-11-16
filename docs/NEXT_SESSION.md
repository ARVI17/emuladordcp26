# Continuación exacta · Club Lab FC27

Corte 16-nov-2026. Prioridad: plantilla competitiva con las cartas reales del propietario. Este incremento corrige la caducidad documental; la aceptación del club real sigue pendiente.

## Al retomar

1. Leer AGENTS, [estado](PROJECT_STATUS.md), [prompt maestro](MASTER_PROMPT.md), [fuentes revisadas](SOURCE_REVIEW_20261116.md) y código/pruebas de la capa afectada.
2. Revisar Git, ramas/worktrees/PR. Checkout C:/Users/arvi_/emuladordcp26; rama codex/revalidar-fc27-20261116, base 0e56d9e de continuidad/PR #9. Conservar la eliminación ajena de .vscode/settings.json. No tocar el worktree emuladordcp26-fc27-planificador (34c4e05).
3. Ejecutar python scripts/project_status.py o powershell -File scripts/fc27.ps1 Memoria. Leer state/continuity/latest.md; distinguir HEAD, SHA servido y alcance/SHA de cada prueba. Ahora incluye vigencia por formación.
4. Actualizar PROJECT_STATE.json al cerrar, ejecutar --render-plan y --check y mantener NEXT_SESSION/TESTING. No editar PROJECT_STATUS a mano ni declarar el producto completo por una suite verde.

## Corrección y evidencia

Se contrastaron las 22 fichas anteriores: veinte siguen documentadas; Nuno Mendes/R33 y Sophia Wilson/R49 quedan pendientes por ambigüedad Standard/Pristine Holographic. R26/R31/R35 siguen pendientes. Las 27 referencias documentadas y los 11 identificadores de formación tienen revisión hasta **16-dic-2026 22:10:56 UTC**, exclusiva. No se renueva evidencia al arrancar.

fc27_formations.json sustituye el corte fijo; prácticas dependen de R09/R16. La migración **0022** modifica exclusivamente las filas exactas del paquete antiguo, conserva evidencia previa y no sobrescribe revisiones locales, posteriores o revocadas. Pruebas de flujo usan copias temporales de evidencia con fechas de prueba; test_public_review.py comprueba los archivos versionados antes/durante/después del intervalo. [Detalle y URLs](SOURCE_REVIEW_20261116.md).

## Instalación y verificación durante la preparación

La instalación personal sigue en **http://localhost:8090**, proyecto emuladordcp26, cinco servicios, versión **8a80860 / 0021** hasta completar el despliegue. PostgreSQL loopback **54326**; volúmenes emuladordcp26_postgres_data y emuladordcp26_ollama_data. No ejecutar Compose de un checkout antiguo.

El respaldo nuevo backups/source-review-before-20261116.dump se restauró en fc27_review_20261116: **46 tablas idénticas, 132 jugadores históricos**, antes de migrar. El ensayo 0022 dejó 44 tablas idénticas y solo cambió catálogo/revisión; 20 variantes vigentes/2 pendientes. El código anterior lee esa copia en READ ONLY. Recuperación preparada en state/source-review-release/original.compose.json; no borrar imágenes/volúmenes. La composición personal canónica continúa en state/visual-scan-release/release.compose.json.

Diagnóstico corregido en dos etapas: 72f8130bf5 tuvo 322 Pytest aprobados/3 fallidos; 1f3fea614e tuvo 325 Pytest y 42 Vitest aprobados, pero 2 Playwright fallaron por otro reloj de octubre del arnés. Ambos relojes de pruebas ya se retiraron; las guardas reales permanecen. Pase corregido 1999b6a92d: 22 Pytest seleccionados, 42 Vitest, 39 Playwright y 14 extensión aprobados; un canvas móvil omitido. Pendiente integral limpio antes de desplegar. Herramientas: 23 pasan. [Resultados](TESTING.md). Los informes acb4979c15 y 65a7a5d1b1 son anteriores a esta corrección.

## Siguiente paso: aceptar el club real

Seguir [REAL_CLUB_FIRST_LOAD](REAL_CLUB_FIRST_LOAD.md): abrir Mi cuenta, seleccionar el contexto correcto, compartir voluntariamente una lista de juego, revisar **20 cartas**, corregir dos, reescanear sin duplicar y proteger **once más siete suplentes**. Cero cartas FC27 activas en la auditoría inicial. No crear inventario desde el catálogo para cerrar este hito.

El OCR de filas sintéticas está comprobado; fichas gráficas EA y selector nativo con el propietario siguen sin contrastar. Ante un fallo, detener/revisar una muestra consentida, mejorar segmentación y repetir regresiones; usar la lectura manual existente si corresponde. No persistir imágenes ni credenciales. No hay adaptador EA de producción y escribir un usuario no conecta la cuenta.

Después: comparar dos alternativas deportivas con datos disponibles; luego revisar un DCP real y cotizaciones de prescindibles/compras. Las guardas de cobertura de mercado en modo visual permanecen. Faltan precios, reglas/puntos de Galería y aceptación real; una venta pendiente no financia una compra. Mantener principal, favoritos, Evos, reservas y consumos protegidos.

## Operación y entrega

    powershell -ExecutionPolicy Bypass -File scripts/fc27.ps1 Estado
    python -m unittest discover -s scripts/tests -v
    python scripts/project_status.py --check
    python scripts/verify_docker.py --scope full --subnet 10.231.27.0/24 --build-environment local

La subred debe estar libre. El verificador usa tmpfs, bloqueo y limpieza por identidad; nunca Pytest contra la base personal. Inicio reutiliza contenedores, no actualiza/migra. Código → pruebas → Docker aislado → diff/secretos → commit → push/SHA remoto → PR en borrador; sin merge automático.
