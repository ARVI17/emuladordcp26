# Modelo del escaneo visual

Reutiliza `CaptureSession`, `VisualReading`, `VisualCopy` y `Player`; migración nueva **0021**, posterior a 0020, añade `CaptureSession.scan_data` y `VisualSnapshot`. No reetiqueta ni elimina cartas existentes.

| Registro | Contenido persistido |
| --- | --- |
| CaptureSession | Contexto/entrada local, origen, estado, vencimiento. scan_data: consentimiento UTC, sección declarada, región porcentual, generación, secuencia, resolución, tiempos, descartes y snapshot. |
| VisualReading | SHA-256, sección/página, candidatas estructuradas, confianza OCR, fecha. El nuevo source_kind es screen_scan; no conserva texto OCR completo. |
| VisualCopy | Relación de lectura/ordinal con copia local revisada, identidad y resolución de dudas. Sigue sin ID de copia EA inventado. |
| VisualSnapshot | Sesión única, snapshot previo enlazado, inventario antes/después, IDs añadidos/actualizados/conservados. removed siempre vacío en este flujo parcial. |

La clave provisional de agrupación usa nombre normalizado, media, posición, variante visible y ordinal de repetición simultánea. Entre vistas, agrupar no prueba que sea la misma instancia. La UI exige revisión explícita de esa hipótesis. Dos filas iguales simultáneas producen dos candidatas. Si el OCR no conoce variante, holografía, rareza o cantidad, siguen desconocidas; no se hace matching canónico ni fuzzy contra un catálogo privado.

`save_reading` mantiene las ambigüedades del dominio. Una etiqueta de variante por sí sola no acredita dos copias distintas. La selección explícita de una copia existente requiere identidad compatible y estado no retirado. El escaneo rechaza coincidencias consumidas antes de guardar; no resucita cartas desde observaciones viejas. La revisión puede corregir campos, excluir candidatas y enlazar copias. El commit selecciona la primera observación de cada grupo aceptado y conserva todas sus observaciones originales en el lote.

La confianza procede del mínimo de palabras TSV de la línea coincidente, no es probabilidad de identidad correcta. Tesseract psm 6 está orientado a listas; la tasa medida sobre fixtures no es precisión sobre cartas reales. Revisión siempre obligatoria incluso con confianza alta.

Estados del servidor: scanning → paused_user/paused_sensitive/needs_review → committing → completed_partial; también failed/cancelled. Pausar, detener, error o salir libera el MediaStream. La UI muestra «Esperando selección de pestaña» antes del permiso y «Escaneo pendiente» cuando no hay sesión. No se emite completed_verified porque no hay evidencia suficiente de cobertura completa. Un proceso cancelado descarta resultados y termina Tesseract; no revive al volver a navegar.

Límites: 4 MB de cuerpo binario, formato/dimensiones verificadas, un OCR global simultáneo, 10 s por pasada (hasta dos si hay ROI), 1 s mínimo entre recepciones, 50 vistas/1000 candidatas, 30 min de vigencia, 20 formularios renderizados por página. No hay Redis ni cola ilimitada. Se conservan sesiones/observaciones estructuradas privadas para revisión, sin vídeos.

## API

Paths internos, prefijo público `/api`:

- `POST /visual-scans`: consentimiento verdadero, origen, sección y región opcional.
- `GET /visual-scans`, `GET /visual-scans/{id}`: resúmenes sin formularios masivos.
- `POST /visual-scans/{id}/frames?sequence=N`: cuerpo binario image/png, image/jpeg o image/webp; anti-replay, privacidad, estabilidad en cliente y control de cola.
- `POST /visual-scans/{id}/transition`: pause, resume, stop o cancel. Las pantallas sensibles no admiten resume: se comparte de nuevo.
- `GET /visual-scans/{id}/candidates?offset=N&limit=20`: revisión paginada.
- `POST /visual-scans/{id}/commit`: cards y frase GUARDAR SINCRONIZACION; atómico/idempotente por sesión y hash del cuerpo.
- `GET /visual-scans/snapshots`, `GET /visual-scans/snapshots/{id}`: historial y diferencias privadas del contexto.

Todas las rutas usan la sesión local/CSRF y el aislamiento ClubScoped existente. Captura y guardado usan bloqueos del contexto/inventario; el OCR no retiene el bloqueo que necesita stop. El resultado se vuelve a contrastar con generación, entrada y contexto antes de persistir.
