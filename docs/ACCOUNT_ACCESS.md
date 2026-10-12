# Cuenta FC27 y versión servida

La entrada **Mi cuenta** abre la Web App oficial en otra pestaña y presenta el estado del planificador por separado. Una sesión local, una API saludable o abrir EA no vinculan la cuenta.

## Bloqueo externo (revisado el 12 de octubre de 2026)

[EA](https://help.ea.com/es/articles/ea-sports-fc/community-api/) identifica FUTBIN, FUT.GG y FUTWIZ como socios aprobados. No consta aprobación para este proyecto ni un protocolo de consentimiento/lectura aplicable. El registro `ADAPTERS` permanece vacío. La autorización HTTP sigue devolviendo 409 y la interfaz ofrece **Actualizar diagnóstico local**, que consulta capacidades sin simular acceso remoto.

Se necesita aprobación específica y documentación de identidad, permisos, consentimiento/retorno, copias, paginación y cuotas antes de implementar un lector de producción. Abrir un socio no transfiere sus permisos. [Acceso oficial de EA](https://help.ea.com/es/articles/ea-sports-fc/early-web-and-companion-app-start/).

## Hechos y límites

`/dashboard.account` separa observaciones remotas del perfil manual. Nombre y saldo se capturan juntos en el manifiesto de la lectura publicada; los snapshots anteriores sin esos datos devuelven desconocido. Una lectura posterior sin monedas no reutiliza el saldo anterior como si fuese reciente. El presupuesto manual permanece en `profile.max_budget`.

El resumen cuenta copias del snapshot, sin confundir ausencia de catálogo público con ausencia de posesión. Las 22 variantes públicas no constituyen el universo del juego. La admisión para cálculos todavía exige el catálogo vigente: normalización específica del proveedor, variantes fuera de la muestra y evoluciones por copia siguen pendientes de un protocolo autorizado; esta entrega no declara resueltos esos casos. No se amplían simulaciones para sustituir la integración. Plantillas remotas, Galería, DCP, evoluciones, objetivos e historial continúan sin reconciliador acreditado. No se dispone de una fuente de arte autorizada por variante en el contrato actual.

Las pruebas usan datos sintéticos y no acreditan lectura de una cuenta personal. El diagnóstico del host, dumps y capturas permanecen en directorios ignorados.

## Build y revisión

Frontend `/build.json`, API `/api/build` y etiquetas OCI de ambas imágenes exponen edición, revisión Git, fecha UTC, entorno y cambios sin confirmar. Los argumentos `BUILD_REVISION`, `BUILD_DATE`, `BUILD_ENVIRONMENT` y `BUILD_DIRTY` deben proceder del checkout que se construye. Sin ellos se indica `unknown`; no se deduce un SHA del nombre de la imagen. `scripts/verify_docker.py` los fija y compara los dos metadatos HTTP tras arrancar Nginx.

La interfaz señala discrepancias entre frontend y API. HTML, service worker y metadatos revalidan su caché; no se borran datos del navegador. Esto no inspecciona ni modifica el perfil personal del navegador.

`docker-compose.review.yml` es una revisión aislada en loopback, normalmente `http://localhost:8081`, sin demo ni proveedor. PostgreSQL usa tmpfs: **no es una instalación permanente** y pierde sus datos al detenerse. No introducir secretos ni el único inventario personal. Antes de detener una revisión existente, clasificar sus datos y respaldar/verificar cualquier dato único. El verificador crea únicamente bases propias desechables en otro puerto.

Actualizar `8080` requiere autorización específica, respaldo verificado, imágenes anteriores conservadas y un plan de rollback con código/base compatibles. No basta hacer push. Las migraciones preservan FC26 aislado; un downgrade no sustituye la restauración de un respaldo. El trabajo apilado debe revisarse junto con sus PR base antes de merge.
