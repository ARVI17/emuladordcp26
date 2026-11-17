# Continuación exacta · Club Lab FC27

Corte **17-nov-2026**, corregido tras la objeción del propietario: **el producto debe actualizarse y analizar automáticamente al abrir, sin escaneos/transcripciones/revisión por carta habituales**. La experiencia actual no satisface esa petición. [Decisión y fuentes de conexión](AUTOMATIC_CLUB_SYNC.md), hito prioritario **AUTO-1**.

**20 cartas personales ya están cargadas**, con seis atributos por carta y posiciones inglesas normalizadas al español. Dos lecturas nuevas de la misma lista conservaron los mismos 20 IDs; cero duplicados añadidos. Se revisaron mediante la interfaz local, no mediante SQL de inserción ni catálogo. Son transcripciones revisadas (`user_reviewed_text / browser_text`), con propiedad declarada y cobertura parcial; la cuenta EA sigue sin autenticación de proveedor. Es un resultado técnico parcial, no aceptación del producto automático.

## Siguiente acción concreta

1. Conservar Chrome conectado, contexto actual y las veinte copias en **http://127.0.0.1:8090/#/club**. No crear otro contexto ni pedir otra transcripción. Evidencia privada anterior: `state/real-first20-20261117/acceptance.json`; no copiar inventario a memoria/Git.
2. Resolver el prototipo de acceso/identidad de **AUTO-1**. EA reserva la API a tres socios y no acepta nuevas solicitudes. WXT es el candidato local; los contratos actuales solo admiten muestras propias. La lista y una ficha reales se leyeron, pero no se encontró ID estable en los atributos inspeccionados. Faltan contraste de identidad/cobertura, navegación automática y permiso persistente; no activar ingestión antes de resolverlos. Comprobar una alternativa de exportación/integración documentada de socios si existe, sin heredar permisos.
3. Probar dos aperturas de la app con veinte copias sin copiar texto ni revisar una por una; cambios, reordenaciones, copias similares, sesión caducada, cancelación y contexto. Distinguir el prototipo, sus pruebas y el servicio instalado; el agente de este chat no es un sincronizador de fondo.
4. Con el conector contrastado, obtener principal por sus puestos y proteger once/siete suplentes, con selección explícita del propietario una vez. No inferir las primeras dieciocho filas ni ampliar texto de plantilla como siguiente solución. Después: tres alternativas, DCP activos posibles/faltantes y ventas propuestas con transferibilidad/ofertas observadas en el mercado PS5. Aún no hay cotizaciones actuales ni ejecución EA.

Esta revisión cambió memoria y criterios, **no desplegó automatización ni modificó aplicación/base/extensión instalada**. No interpretar las fuentes consultadas ni la navegación puntual del agente como un adaptador de producción.

## Versión y recuperación

Código probado y servido: **c9d7a7859ca329e57df82ec02c0394439ee0eff7 / 0022**, puerto **8090**, cinco servicios saludables. Solo se recrearon backend/frontend; database/nginx/ollama conservaron ID y arranque, y los volúmenes permanecieron intactos. No hubo migración. La carga real conservó exactamente los **132 registros históricos retirados**. HEAD puede avanzar por documentación; consultar `python scripts/project_status.py` para separarlo de la imagen servida.

Trabajo: `C:/Users/arvi_/.codex/worktrees/fc27-source-review-verification/emuladordcp26`, rama `codex/wxt-first20-20261116`, [PR #11 en borrador](https://github.com/ARVI17/emuladordcp26/pull/11), sin merge. Conservar la eliminación ajena de `.vscode/settings.json` en el checkout original.

En `C:/Users/arvi_/emuladordcp26`, el respaldo **backups/browser-text-before-20261117.dump** se restauró en `fc27_text_20261117`: 46 tablas idénticas y 132 históricos. Recuperación: `state/browser-text-release-20261117/original.compose.json`, imágenes anteriores preservadas. La composición canónica `state/visual-scan-release/release.compose.json` apunta a c9d7a78. Evidencia de despliegue: `state/browser-text-release-20261117/live-checks.json`. También se guardó **backups/browser-text-first20-20261117.dump** después de las tres revisiones reales; ese segundo dump no se restauró de nuevo. No sobrescribir la base personal para ensayarlo.

## Comprobaciones y límites

Dos pases corregidos sobre el mismo código limpio: focalizado **c0bcc46c8b** (69 Pytest, 43 Vitest, 2 Playwright, 15 WXT) e integral **5a5761c626** (366 Pytest, 43 Vitest, 41 Playwright, 15 WXT; un canvas móvil omitido). Build, salud/OpenAPI, Alembic y limpieza aprobados; instalación personal y volúmenes intactos durante las pruebas. Herramientas: 23 pruebas aprobadas. Los fallos previos y sus correcciones están en [TESTING](TESTING.md). [CI del código aprobada](https://github.com/ARVI17/emuladordcp26/actions/runs/44081146919), comprobada después de la carga personal.

Aceptación personal: lecturas 1, 2 y 3 revisadas desde la UI, 20 copias en cada una, nombres/medias/posiciones contrastados con la lista visible, seis atributos por carta, mismos IDs y ningún histórico modificado. La comprobación privada posterior usó una transacción de solo lectura. No se persistieron capturas, credenciales ni inventario en Git. No se certificó el OCR de fichas gráficas reales: sus dos rechazos del 16-nov siguen documentados. Los ensayos de corrección de dos campos y de once más siete protegidos son sintéticos; la principal personal sigue pendiente.

La carga anterior usó Chrome conectado/Playwright para leer elementos visibles y revisión local de texto. No fue sincronización automática ni paginación completa. WXT 0.5.1 conserva sus pruebas y artefacto privado, pero no se cargó en Chrome por el bloqueo del administrador de extensiones. No repetir esa instalación como si habilitara AUTO-1: ese artefacto aún carece de lector EA. No eludir el bloqueo por otra superficie. Cualquier distribución futura debe venir después de un prototipo probado y declarar los permisos nuevos concretos. [Contrato asistido](ASSISTED_READING.md), [carga anterior](REAL_CLUB_FIRST_LOAD.md).

Operación: `powershell -ExecutionPolicy Bypass -File scripts/fc27.ps1 Estado`, `python scripts/project_status.py --check`. Actualizar PROJECT_STATE y regenerar la vista al cerrar cada sprint. No hay agente de fondo que actualice el juicio funcional.
