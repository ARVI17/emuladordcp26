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
