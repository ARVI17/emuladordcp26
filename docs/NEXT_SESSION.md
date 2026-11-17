# Continuación exacta · Club Lab FC27

Corte 16-nov-2026. Prioridad: plantilla competitiva con las cartas reales del propietario. **Chrome ya está conectado** y se leyó la lista de veinte cartas mediante su interfaz. Cero cartas admitidas: el OCR real se rechazó en dos lecturas independientes. El propietario pide simplificar y usar opciones gratuitas. La instalación personal sigue en 96a8d21/0022.

## Relevo de Chrome y WXT

Trabajo actual en `C:/Users/arvi_/.codex/worktrees/fc27-source-review-verification/emuladordcp26`, rama `codex/wxt-first20-20261116`. Código WXT publicado en **7dbad26**, base a8bd539; [PR #11 en borrador](https://github.com/ARVI17/emuladordcp26/pull/11), CI aprobada. La rama anterior y PR #10 permanecen sin merge. Conservar la eliminación ajena de `.vscode/settings.json` en el checkout original.

El propietario inició sesión en EA por su cuenta, abrió sus cartas y autorizó al agente a hacer la lectura y selección de pestaña. Los primeros turnos pararon por URL no verificable, sin llegar al OCR. Después autorizó expresamente instalar la extensión oficial de ChatGPT; su instalación/conexión se verificó y el navegador expuso la pestaña EA correcta. No volver a pedir esa instalación ni copiar perfiles/cookies o usar CDP directo.

La conexión oficial del chat y WXT son extensiones distintas. WXT aparece instalado en la barra de Chrome, versión no contrastada. La política del control del navegador rechazó abrir `chrome://extensions`; **no se cargó la actualización 0.5.1** ni se eludió el rechazo mediante otra superficie. El artefacto probado está en `state/wxt-first20-release/chrome-mv3`, con hashes y procedencia en `artifact.json`, extraído de la imagen `emuladordcp26-check-390af9b380:extension-test`. [Guía de la conexión oficial](https://learn.chatgpt.com/docs/chrome-extension).

WXT 0.5.1 corrige `resultú.groups` por `result?.groups`: antes podía interrumpirse la actualización del panel al existir un informe, tanto pendiente como calculado. La nueva prueba usa Chromium temporal y PostgreSQL tmpfs: veinte cartas sintéticas, dos nuevas lecturas que reutilizan los mismos veinte IDs, repetición de revisión, principal explícita de once más siete y rechazo de archivo de sus dieciocho copias. No se infiere principal por orden de inventario. Pases **c4424a006a / 390af9b380: 15 pruebas aprobadas en cada uno**, instalación y volúmenes intactos. Resultados en TESTING.md.

Aceptación personal al corte: **20 filas reales legibles por DOM, 0 cartas guardadas, principal real sin registrar**. Se seleccionó únicamente EA en el permiso nativo; Club Lab mostró captura activa. Dos sesiones de captura y dos pulsaciones de Leer pantalla devolvieron «Pantalla ajena, sensible, de otra edición o ilegible. Selecciona otra pantalla.»; la captura terminó y no hubo lectura revisable. Esto sí es un rechazo real del reconocimiento. No atribuirlo al acceso a Chrome ni afirmar su causa exacta sin diagnóstico: la revisión de código detecta además que `parse_screen` y `extract_inventory_candidates` esperan marcas/posiciones españolas, mientras la vista es inglesa. No se persistieron capturas ni se anotan cartas privadas aquí.

## Decisión para simplificar

Se contrastaron documentación oficial y repositorios, sin instalar herramientas nuevas. [Comparación y fuentes](REAL_CLUB_FIRST_LOAD.md#rutas-gratuitas-contrastadas-16-nov-2026). **FUTWIZ Squad Sync** es la opción lista más sencilla para consultar plantillas con conexión oficial y gratuita; no acredita exportación del inventario completo a Club Lab. FC-Tracker es gratuito para uso personal y útil para Galería, con licencia restrictiva y sincronización no oficial. FC27 Copilot es MIT, pero exige otra extensión, servicio y cliente MCP; no reduce esta configuración. WXT/Playwright ya existen en el proyecto; añadir Puppeteer, otro daemon o un solver no arregla la admisión.

Siguiente incremento local: acotar el lector a una región visible y revisable de veinte cartas, normalizar posiciones EN/ES y comprobar variantes/copias antes de enviar a la revisión existente. Primero contrastar el lector instalado; una actualización de WXT sigue requiriendo la carga por el propietario donde la herramienta bloquea el administrador. Revisar los límites reales de `inspect-region.ts`/`profile-extraction.ts` (ancestros de listas, profundidad y coincidencia literal de clases) antes de prometer un botón automático. Si se trabaja en OCR, reproducir el rechazo y la segmentación con datos sintéticos equivalentes, sin quitar la guarda de pantallas sensibles. No pasar texto observado por CSV como si fuese evidencia de propiedad ni activar una muestra sintética. `Analizar mi club` aún solo extrae automáticamente el esquema propio.

Después de la primera admisión: dos nuevas lecturas deben conservar los veinte IDs; leer la principal por separado y proteger once más siete. Mantener el contexto asistido seleccionado: la UI contiene varias etiquetas iguales; no crear otro por una lista vacía. No guardar nombres, inventarios, imágenes o credenciales en esta memoria.

## Al retomar

1. Leer AGENTS, [estado](PROJECT_STATUS.md), [prompt maestro](MASTER_PROMPT.md), [fuentes revisadas](SOURCE_REVIEW_20261116.md) y código/pruebas de la capa afectada.
2. Revisar Git, ramas/worktrees/PR. Checkout C:/Users/arvi_/emuladordcp26; rama codex/revalidar-fc27-20261116, base 0e56d9e de continuidad/PR #9. Conservar la eliminación ajena de .vscode/settings.json. No tocar el worktree emuladordcp26-fc27-planificador (34c4e05).
3. Ejecutar python scripts/project_status.py o powershell -File scripts/fc27.ps1 Memoria. Leer state/continuity/latest.md; distinguir HEAD, SHA servido y alcance/SHA de cada prueba. Ahora incluye vigencia por formación.
4. Actualizar PROJECT_STATE.json al cerrar, ejecutar --render-plan y --check y mantener NEXT_SESSION/TESTING. No editar PROJECT_STATUS a mano ni declarar el producto completo por una suite verde.

## Corrección y evidencia

Se contrastaron las 22 fichas anteriores: veinte siguen documentadas; Nuno Mendes/R33 y Sophia Wilson/R49 quedan pendientes por ambigüedad Standard/Pristine Holographic. R26/R31/R35 siguen pendientes. Las 27 referencias documentadas y los 11 identificadores de formación tienen revisión hasta **16-dic-2026 22:10:56 UTC**, exclusiva. No se renueva evidencia al arrancar.

fc27_formations.json sustituye el corte fijo; prácticas dependen de R09/R16. La migración **0022** modifica exclusivamente las filas exactas del paquete antiguo, conserva evidencia previa y no sobrescribe revisiones locales, posteriores o revocadas. Pruebas de flujo usan copias temporales de evidencia con fechas de prueba; test_public_review.py comprueba los archivos versionados antes/durante/después del intervalo. [Detalle y URLs](SOURCE_REVIEW_20261116.md).

## Instalación personal actualizada

Instalación personal **http://localhost:8090**, proyecto emuladordcp26, **cinco servicios saludables**, código **96a8d215dc71641885e35ec472f0ecc1e95c2a17 / 0022**, construcción limpia local. Imágenes exactas del integral f98e7366f4. Comprobados 11 identificadores de formación, 2 artículos y 6 prácticas vigentes. PostgreSQL loopback **54326**; volúmenes emuladordcp26_postgres_data y emuladordcp26_ollama_data conservados. Solo se recrearon backend/frontend; database/nginx/ollama conservaron ID y arranque. Nginx recargado.

El respaldo nuevo backups/source-review-before-20261116.dump se restauró en fc27_review_20261116: **46 tablas idénticas, 132 jugadores históricos**, antes de migrar. El ensayo 0022 dejó 44 tablas idénticas y solo cambió catálogo/revisión; 20 variantes vigentes/2 pendientes. El código anterior lee esa copia en READ ONLY. Recuperación preparada en state/source-review-release/original.compose.json; no borrar imágenes/volúmenes. La composición personal canónica state/visual-scan-release/release.compose.json y su release-evidence.json apuntan ahora a las imágenes de 96a8d21. La comprobación posterior al despliegue también conserva 44 tablas y los 132 jugadores retirados; cero cartas FC27 activas. Evidencia privada: state/source-review-release/live-checks.json e integrity-fc26.json.

Diagnóstico corregido en dos etapas: 72f8130bf5 tuvo 322 Pytest aprobados/3 fallidos; 1f3fea614e tuvo 325 Pytest y 42 Vitest aprobados, pero 2 Playwright fallaron por otro reloj de octubre del arnés. Ambos relojes de pruebas ya se retiraron; las guardas reales permanecen. Pase corregido 1999b6a92d: 22 Pytest seleccionados, 42 Vitest, 39 Playwright y 14 extensión aprobados; un canvas móvil omitido. Integral limpio f98e7366f4 sobre 96a8d21: 325 Pytest, 42 Vitest, 39 Playwright y 14 extensión aprobados, con un canvas móvil omitido. CI del código aprobada. Informes copiados al state/sprints del checkout principal y capturas sintéticas en state/source-review-release/screens-clean. El checkout limpio de verificación se conserva en C:/Users/arvi_/.codex/worktrees/fc27-source-review-verification/emuladordcp26: Codex rechazó archivarlo porque lo considera el checkout principal del chat; tampoco admite adjuntar el repositorio principal como worktree enlazado. No se forzó su borrado. Se actualiza al commit final de pruebas/documentación para conservar este relevo. No es otra aplicación en ejecución. La configuración privada de despliegue y los respaldos están en el checkout original C:/Users/arvi_/emuladordcp26. [PR #10 en borrador](https://github.com/ARVI17/emuladordcp26/pull/10), apilado sobre #9, sin merge. Los commits posteriores de pruebas/documentación no cambian la aplicación servida; HEAD/remoto se consultan en el diagnóstico. Herramientas: 23 pasan. [Resultados](TESTING.md). Los informes acb4979c15 y 65a7a5d1b1 son anteriores a esta corrección.

Después del cierre documental, CI detectó una espera de 5 s insuficiente para el acuse de cambio de contexto en la prueba de extensión (13 pasan/1 falla; las otras tres tareas CI pasan). Se acota a 15 s conforme al transporte y se exige además comprobar la pausa directamente y conservar 366 cartas tras mostrar otro contexto. Solo cambia el test; la aplicación servida sigue en 96a8d21/0022. Repeticiones aisladas a455aed1ab y 3ee4a35806: 14 pasan en cada una, instalación y volúmenes intactos. Consultar TESTING.md y PR #10 para el estado final de CI; no confundir este fallo con aceptación real del club.

## Siguiente paso: aceptar el club real

Seguir [REAL_CLUB_FIRST_LOAD](REAL_CLUB_FIRST_LOAD.md): abrir Mi cuenta, seleccionar el contexto correcto, compartir voluntariamente una lista de juego, revisar **20 cartas**, corregir dos, reescanear sin duplicar y proteger **once más siete suplentes**. Cero cartas FC27 activas en la auditoría inicial. No crear inventario desde el catálogo para cerrar este hito.

El OCR de filas sintéticas está comprobado; fichas gráficas EA y selector nativo con el propietario siguen sin contrastar. Ante un fallo, detener/revisar una muestra consentida, mejorar segmentación y repetir regresiones; usar la lectura manual existente si corresponde. No persistir imágenes ni credenciales. No hay adaptador EA de producción y escribir un usuario no conecta la cuenta.

Después: comparar al menos tres alternativas deportivas con datos disponibles; luego revisar un DCP real y cotizaciones de prescindibles/compras. Las guardas de cobertura de mercado en modo visual permanecen. Faltan precios, reglas/puntos de Galería y aceptación real; una venta pendiente no financia una compra. Mantener principal, favoritos, Evos, reservas y consumos protegidos.

## Operación y entrega

    powershell -ExecutionPolicy Bypass -File scripts/fc27.ps1 Estado
    python -m unittest discover -s scripts/tests -v
    python scripts/project_status.py --check
    python scripts/verify_docker.py --scope full --subnet 10.231.27.0/24 --build-environment local

La subred debe estar libre. El verificador usa tmpfs, bloqueo y limpieza por identidad; nunca Pytest contra la base personal. Inicio reutiliza contenedores, no actualiza/migra. Código → pruebas → Docker aislado → diff/secretos → commit → push/SHA remoto → PR en borrador; sin merge automático.
