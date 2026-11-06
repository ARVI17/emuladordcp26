# Cambios del incremento visual · 5 de noviembre de 2026

## Base conservada

Checkout inicial `ffcf7e0`/0005; instalación personal `ea27c61`/0019; desarrollo sobre `34c4e05`/0020 en rama nueva `agent/visual-capture-fc27-20261105`. No se fusionó main ni se alteró el worktree `agent/fc27-dom-gallery`. Commit de auditoría: `73aaa37`.

## Cambio de aplicación

Antes: captura manual por observación y lector estructurado previo. Ahora: muestreo voluntario de vistas estables, máscaras antes del envío, región opcional, parada real, candidatos acumulados y revisión de hasta 20 formularios por página. El guardado produce diferencias antes/después, conserva lo no visto y exige confirmación de propiedad/identidad. Se reutilizan contextos, protección/ambigüedad, sesiones y auditoría. No añade acceso a EA ni automatización de acciones.

Migración aditiva **0021**: JSON `capture_sessions.scan_data` y tabla `visual_snapshots`, con enlace al lote y snapshot anterior. Partir de 0019 también aplica 0020 heredada. No cambia físicamente cartas ni elimina históricos; downgrade no es una estrategia de recuperación de datos únicos.

El verificador admite subred privada explícita libre cuando Docker agotó sus pools. Conserva las guardas y la limpieza exclusiva de recursos de prueba. No añade servicios ni dependencias de ejecución.

## Compatibilidad y recuperación

Las rutas previas siguen disponibles. El nuevo endpoint recibe cuerpo binario de imagen, no FormData. Versiones de backend/frontend deben coincidir; `/build.json` y `/api/build` lo acreditan. Antes de migrar la instalación se conserva dump, composición original e IDs de imágenes, y se comprueba restauración/migración en una base separada. En caso de fallo, mantener la base nueva intacta; restaurar el respaldo en otra base y arrancar las imágenes anteriores apuntando a ella tras revisar el resultado. No restaurar primero sobre datos únicos ni bajar el esquema automáticamente.

Historial de ejecución y resultados: [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md). Despliegue efectivo y siguiente paso: [NEXT_SESSION.md](NEXT_SESSION.md).

## Commits propios

- `73aaa37`: auditoría y respaldo inicial.
- `1b5c1ff`: escáner, OCR cancelable, API, migración, UI, pruebas y documentación del alcance.
- `94cb337`: compatibilidad de migración SQLite y entornos CI; no cambia las protecciones de captura.
- `8a80860`: expectativa E2E actualizada para la guía nueva de cuenta; mantiene la comprobación de cuenta no vinculada.
- `d3838e7` y `855fd0f`: reloj determinista para comprobar el límite de frecuencia en máquinas lentas; cambios exclusivos de pruebas.

El commit de cierre registra despliegue, pruebas, recuperación y continuidad; también hace que la prueba heredada de reanudación espere la respuesta del cálculo y verifique su estado. No modifica código de aplicación. Identifica su SHA mediante `git log -1`; no se sustituye retroactivamente el SHA servido 8a80860 por el de documentación.

Rama publicada y [PR #8 en borrador](https://github.com/ARVI17/emuladordcp26/pull/8), apilada sobre `agent/fc27-dom-gallery`. No se fusionó ninguna rama. Los resultados de cada intento, incluidos fallos corregidos, se conservan en IMPLEMENTATION_STATUS y los informes privados.

## Antes y después en la instalación personal

| Aspecto | Antes | Después |
| --- | --- | --- |
| Código/esquema | ea27c61 / 0019, servicios detenidos | 8a80860 / 0021, cinco servicios saludables |
| Lectura visual | Una lectura manual por acción | Lote de vistas estables consentido, pausa y revisión explícita |
| Guardado del lote | Observaciones revisadas previas | Snapshot enlazado antes/después, commit idempotente, ausentes conservados |
| Datos de jugadores | 132 retirados / 0 activos | 132 retirados / 0 activos, sin fixtures personales |
| Acceso | Nginx 8090; PostgreSQL 55432 reservado por Windows | Nginx 127.0.0.1:8090; PostgreSQL 127.0.0.1:54326 |
| EA/precios/compras | Sin acceso autorizado a proveedor | Sin acceso autorizado a proveedor; siguientes etapas pendientes |

Se usan los mismos volúmenes. La restauración con la imagen anterior y la migración poblada se ensayaron en copias; antes de abrir Nginx, las 43 tablas de datos anteriores conservaron hashes/recuentos. Composición actual y anterior fijadas por image ID en `state/visual-scan-release/`, fuera de Git. Las imágenes servidas corresponden a la revisión de aplicación probada; commits posteriores solo ajustan pruebas/documentación.
