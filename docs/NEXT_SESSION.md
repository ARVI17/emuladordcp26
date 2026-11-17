# Continuación exacta · Club Lab FC27

Corte **17-nov-2026**. Prioridad: una plantilla competitiva con el club real. **20 cartas personales ya están cargadas**, con seis atributos por carta y posiciones inglesas normalizadas al español. Dos lecturas nuevas de la misma lista conservaron los mismos 20 IDs; cero duplicados añadidos. Se revisaron mediante la interfaz local, no mediante SQL de inserción ni catálogo. Son transcripciones revisadas (`user_reviewed_text / browser_text`), con propiedad declarada y cobertura parcial; la cuenta EA sigue sin autenticación de proveedor.

## Siguiente acción concreta

1. Reutilizar Chrome conectado y el contexto asistido ya seleccionado en **http://127.0.0.1:8090/#/club**. No crear otro contexto homónimo. La evidencia privada `state/real-first20-20261117/acceptance.json` contiene contexto, recibos e IDs; no copiar el inventario a memoria o Git. La pestaña oficial EA queda disponible para continuar; el propietario inicia sesión si caduca.
2. Abrir la **plantilla activa en EA** y observar sus once puestos y siete suplentes. No considerar principales las primeras 18 cartas de la lista. Contrastar la formación y reutilizar las copias ya cargadas cuando se pueda demostrar correspondencia.
3. Registrar una observación de ámbito **Mi principal**, revisar puestos y confirmar `REGISTRAR MI PRINCIPAL`. La entrada de texto nueva solo admite inventario: no acredita puestos ni crea una principal. Si el OCR de plantilla no ofrece candidatas fiables, el siguiente incremento debe admitir texto de plantilla con puestos explícitos y el mismo comprobante de propiedad/copia, sin modificar a mano el ámbito de recibos existentes. Proteger todas las copias del once y banquillo; conservar también reservas/favoritos/Evos pertinentes.
4. Completar variante, liga, club, nacionalidad, cesión, Evo, transferibilidad y posiciones alternativas solo con evidencia. Después comparar tres alternativas deportivas con sus carencias. DCP, precios, ventas propuestas, fichajes y Galería vienen después de identificar/proteger la principal. No hay precios actuales acreditados ni operaciones EA automáticas.

## Versión y recuperación

Código probado y servido: **c9d7a7859ca329e57df82ec02c0394439ee0eff7 / 0022**, puerto **8090**, cinco servicios saludables. Solo se recrearon backend/frontend; database/nginx/ollama conservaron ID y arranque, y los volúmenes permanecieron intactos. No hubo migración. La carga real conservó exactamente los **132 registros históricos retirados**. HEAD puede avanzar por documentación; consultar `python scripts/project_status.py` para separarlo de la imagen servida.

Trabajo: `C:/Users/arvi_/.codex/worktrees/fc27-source-review-verification/emuladordcp26`, rama `codex/wxt-first20-20261116`, [PR #11 en borrador](https://github.com/ARVI17/emuladordcp26/pull/11), sin merge. Conservar la eliminación ajena de `.vscode/settings.json` en el checkout original.

En `C:/Users/arvi_/emuladordcp26`, el respaldo **backups/browser-text-before-20261117.dump** se restauró en `fc27_text_20261117`: 46 tablas idénticas y 132 históricos. Recuperación: `state/browser-text-release-20261117/original.compose.json`, imágenes anteriores preservadas. La composición canónica `state/visual-scan-release/release.compose.json` apunta a c9d7a78. Evidencia de despliegue: `state/browser-text-release-20261117/live-checks.json`. También se guardó **backups/browser-text-first20-20261117.dump** después de las tres revisiones reales; ese segundo dump no se restauró de nuevo. No sobrescribir la base personal para ensayarlo.

## Comprobaciones y límites

Dos pases corregidos sobre el mismo código limpio: focalizado **c0bcc46c8b** (69 Pytest, 43 Vitest, 2 Playwright, 15 WXT) e integral **5a5761c626** (366 Pytest, 43 Vitest, 41 Playwright, 15 WXT; un canvas móvil omitido). Build, salud/OpenAPI, Alembic y limpieza aprobados; instalación personal y volúmenes intactos durante las pruebas. Herramientas: 23 pruebas aprobadas. Los fallos previos y sus correcciones están en [TESTING](TESTING.md). [CI del código aprobada](https://github.com/ARVI17/emuladordcp26/actions/runs/44081146919), comprobada después de la carga personal.

Aceptación personal: lecturas 1, 2 y 3 revisadas desde la UI, 20 copias en cada una, nombres/medias/posiciones contrastados con la lista visible, seis atributos por carta, mismos IDs y ningún histórico modificado. La comprobación privada posterior usó una transacción de solo lectura. No se persistieron capturas, credenciales ni inventario en Git. No se certificó el OCR de fichas gráficas reales: sus dos rechazos del 16-nov siguen documentados. Los ensayos de corrección de dos campos y de once más siete protegidos son sintéticos; la principal personal sigue pendiente.

La vía usada es Chrome conectado/Playwright para leer elementos visibles y la revisión local de texto. No requiere actualizar WXT ni instalar Scrapy, Selenium o un servicio Python. No es sincronización automática ni paginación completa. WXT 0.5.1 conserva sus pruebas y artefacto privado, pero no se cargó en Chrome por el bloqueo del administrador de extensiones; no volver a pedir esa instalación para continuar este recorrido. [Contrato](ASSISTED_READING.md), [guía actual](REAL_CLUB_FIRST_LOAD.md).

Operación: `powershell -ExecutionPolicy Bypass -File scripts/fc27.ps1 Estado`, `python scripts/project_status.py --check`. Actualizar PROJECT_STATE y regenerar la vista al cerrar cada sprint. No hay agente de fondo que actualice el juicio funcional.
