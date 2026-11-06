# Continuación exacta · incremento visual FC27

Trabaja en `C:\Users\arvi_\emuladordcp26`, rama **agent/visual-capture-fc27-20261105**, basada en `34c4e05`, no en el checkout viejo `ffcf7e0`/0005. Lee AGENTS, PROJECT_MAP, IMPLEMENTATION_STATUS, OCR_DATA_MODEL y USER_LOGIN_AND_VISUAL_SCAN. No reconstruyas ni migres desde la rama antigua. No toques los cambios/worktree `emuladordcp26-fc27-planificador`.

## Datos y operación

- Única instalación personal: proyecto Compose `emuladordcp26`, URL **http://localhost:8090**. Puerto 8080 es solo el predeterminado del repositorio.
- Volúmenes que se preservan: `emuladordcp26_postgres_data`, `emuladordcp26_ollama_data`. Respaldo inicial ignorado por Git: `backups/visual-scan-before-20261105.dump`.
- Estado inicial real: 0019, 44 tablas, 132 jugadores retirados, cero activos. No son evidencia del club EA. Base restaurada separada: `fc26_verify_visual_20261105`.
- Windows reservó 55432; PostgreSQL quedó en 127.0.0.1:54326. Conserva .env y configuraciones privadas fuera de Git.
- `powershell -File scripts/fc27.ps1 Estado` y `/api/build` acreditan imágenes servidas. No asumir que HEAD coincide con el contenedor.

## Estado entregado de la instalación

Se actualizó la instalación local a **8a80860 / 0021** con las imágenes exactas del pase integral **dc69595a37**: 319 Pytest, 42 Vitest, 39 Playwright y 14 pruebas de extensión aprobados; una prueba de captura móvil omitida. Los commits `d3838e7`/`855fd0f` corrigen exclusivamente el reloj de un test para CI; el pase focalizado **6a377aee90** aprobó los 13 casos nuevos. Los commits posteriores de documentación tampoco cambian la aplicación servida.

El cierre también corrige exclusivamente la espera de `frontend/e2e/analyze-club.spec.ts`: reanudar espera la respuesta HTTP real y valida status active, en vez de asumir que el cálculo termina antes de cinco segundos. El pase **42cbb3ebe2** aprobó 42 Vitest y ambos recorridos móvil/escritorio. No reconstruir la aplicación solo para incorporar cambios de tests/documentación; el código desplegable permanece igual a 8a80860. Comprueba los checks actuales de la PR antes de concluir el estado de CI.

Composición privada actual: `state/visual-scan-release/release.compose.json`; recuperación: `original.compose.json` e imágenes anteriores, además del dump. `release-evidence.json`, `external-checks.json`, `integrity-before.json`, `integrity-fc26.json` y logs documentan los checks. Backend fijado `sha256:0a6afeb5821213bae2436f4550c4eb404cf9efcb9c03b1eb8c7232f623be60a4`; frontend `sha256:82f3cebbf431597a3c14ad6eff8fc2573580593f887840f7c3ab6503c7c6e131`. Los cinco servicios están saludables; Nginx 127.0.0.1:8090 y PostgreSQL **127.0.0.1:54326**. No uses el Compose predeterminado para recrear esta instalación: .env se conservó y 55432 está reservado por Windows. `scripts/fc27.ps1 Inicio|Estado|Parada` reutiliza los contenedores correctos.

Base personal antes/después: 43 tablas de datos previos idénticas por hash/recuento; alembic_version pasa 0019→0021; reader_workflows/visual_snapshots nuevas y vacías al entregar. **132 jugadores retirados, cero activos**. Se conservan dos copias de verificación identificadas: `fc26_verify_visual_20261105` y `fc26_verify_visual_final_20261105`, ambas migradas a 0021; la segunda se comprobó también con imagen ea27c61/esquema 0019 antes de migrarla. No son nuevas instalaciones públicas. No eliminarlas como si fueran datos de terceros.

Rama enviada, [PR #8 en borrador](https://github.com/ARVI17/emuladordcp26/pull/8), base `agent/fc27-dom-gallery`; sin merge a main ni despliegue externo. El estado de CI se registra en IMPLEMENTATION_STATUS y en la PR. La prueba de sesión EA, selector nativo real, Safari, hardware ADB e inferencia GPU no se ejecutó.

## Siguiente trabajo

1. Revisar los resultados definitivos al pie de IMPLEMENTATION_STATUS y el estado de Git/stack. No repetir suites completas sin cambio/fallo que lo justifique.
2. Validación humana del MVP: compartir una vista del club ya abierta, observar 20 cartas, corregir dos y revisar variantes/copias. No afirmar precisión antes de esa prueba. No pedir credenciales ni sesión automatizada; no capturar login/MFA. Si el formato gráfico no se reconoce, conseguir una muestra permitida y mejorar segmentación/extractor con pruebas A/B. Los tests actuales reconocen filas sintéticas legibles.
3. Añadir correspondencia canónica/variantes y resolución explícita de grupos que representan copias distintas entre páginas. Hoy se marcan inciertos y requieren leer fichas por separado. No elevar confianza OCR a certeza de propiedad/variante.
4. Etapa 2: conectar lectura de un DCP tradicional y uno simplificado verificados al flujo; conservar origen/fecha/progreso. Ver FC27_DCP_RULES.
5. Etapas 3–4: importación de precios permitidos con variante/plataforma/fecha; solvers con compras, presupuesto y coste de oportunidad. Probar mínimo por enumeración pequeña y status FEASIBLE_NOT_PROVEN. No habilitar FUTBIN/FUT.GG/FUTWIZ sin autorización/documentación que aplique al proyecto.
6. Seguir etapas 5–7 del prompt original, sin declarar completado el objetivo global por tener UI previa.

## Verificación reproducible

`python scripts/verify_docker.py --scope full --subnet 10.231.27.0/24 --build-environment local` usa solo tmpfs, puerto 8082 y recursos propios. Elige otra /24 privada libre si hay solapamiento; no borres redes ajenas. Logs/resultados en `state/sprints/`. Para diagnosticar: añadir `--pytest-path test_visual_scan.py --browser-spec visual-scan.spec.ts`; luego repetir integral si hubo cambios.

La prueba de navegador usa canvas sintético y un proxy loopback efímero dentro del contenedor para ejercitar un origen seguro real; no modifica producción. No existe prueba de sesión EA, botón nativo de permiso real ni credenciales. No instalar la extensión previa para el nuevo flujo. Ollama/ADB no son necesarios; el comportamiento sin ellos forma parte del arranque aislado.
