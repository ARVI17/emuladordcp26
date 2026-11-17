# Continuación exacta · Club Lab FC27

Corte **17-nov-2026 · WXT 0.6.0**. Ya hay código de actualización al abrir: extensión local, navegación DOM EN/ES, primera lista de veinte, plantilla por puestos, conciliación idempotente y candados. **Aceptación automática personal pendiente**. No volver a proponer capturas/transcripciones como recorrido habitual. [Contrato y límites](AUTOMATIC_CLUB_SYNC.md), [pruebas](TESTING.md).

## Siguiente acción concreta

1. Comprobar los pases Docker y el artefacto 0.6.0; no instalar el antiguo 0.5.1, que carece del lector EA automático. Confirmar build servido/esquema con `python scripts/project_status.py` y OpenAPI real.
2. Instalar/actualizar la extensión probada en el perfil personal. El agente recibió un bloqueo de `chrome://extensions`; no eludirlo mediante otra superficie, CDP o cambios de perfil. El propietario debe cargar el artefacto una vez. Nuevos permisos: localhost/127.0.0.1 y `www.ea.com`; sin cookies/debugger/historial ni dominio de autenticación.
3. Activar una vez en Mi cuenta y abrir la app dos veces: debe iniciar sola, conservar los IDs de las veinte copias y proteger once/siete suplentes más reservas visibles. Las cartas de la principal ajenas a esa primera lista son copias adicionales, no duplicados por aumentar el total. Verificar recibos/correspondencia, no solo conteo.
4. Si EA caduca, el propietario accede; el lector conserva fecha/datos anteriores. No forzar fusión de variantes indistinguibles. El nombre de club no prueba identidad de cuenta; la firma visual no es ID estable EA. Mantener guardas de consumo/venta.
5. Tras aceptación: tres alternativas competitivas, DCP vigentes y ofertas reales PS5 con procedencia/fecha. Este sprint no implementa extracción de mercado/DCP ni acciones económicas.

## Evidencia personal

Las **20 copias reales anteriores** permanecen en el contexto existente, seis atributos y procedencia `user_reviewed_text / browser_text`, con IDs conservados en dos relecturas y 132 históricos intactos. Evidencia privada anterior: `state/real-first20-20261117/acceptance.json`. No copiar nombres, inventario ni secretos a Git/memoria.

EA mostró inicialmente `Cannot Authenticate`; después volvió a mostrar las cartas. Se contrastaron lista, Player Bio y Active Squad sin credenciales ni API privada. La principal observada tiene once, siete suplentes y cuatro reservas. El campo oculta nombres; ambos bancos comparten clase y se distinguen por leyenda; la ficha de plantilla requiere dos regresos. Esas diferencias se incorporaron al lector. No se cargó/protegió la principal mediante una transcripción alternativa. Inglés contrastado personalmente; español solo con fixture. Navegación puntual del agente no acredita WXT instalado ni aceptación automática.

Privacidad: datos del club a loopback. Los socios oficiales no reciben contraseña mediante la conexión EA, pero sí datos autorizados. WXT no es socio aprobado y las reglas EA prohíben automatizaciones no autorizadas: no prometer ausencia de sanción. Fuentes en AUTOMATIC_CLUB_SYNC.

## Versión y recuperación

Servicio personal acreditado antes de este incremento: **c9d7a7859ca329e57df82ec02c0394439ee0eff7 / 0022**, puerto **8090**, cinco servicios saludables. Solo se recrearon backend/frontend; database/nginx/ollama conservaron ID y arranque, y los volúmenes permanecieron intactos. No hubo migración. La carga real conservó exactamente los **132 registros históricos retirados**. HEAD puede avanzar por documentación; consultar `python scripts/project_status.py` para separarlo de la imagen servida.

Trabajo: `C:/Users/arvi_/.codex/worktrees/fc27-source-review-verification/emuladordcp26`, rama `codex/wxt-first20-20261116`, [PR #11 en borrador](https://github.com/ARVI17/emuladordcp26/pull/11), sin merge. Conservar la eliminación ajena de `.vscode/settings.json` en el checkout original.

En `C:/Users/arvi_/emuladordcp26`, el respaldo **backups/browser-text-before-20261117.dump** se restauró en `fc27_text_20261117`: 46 tablas idénticas y 132 históricos. Recuperación: `state/browser-text-release-20261117/original.compose.json`, imágenes anteriores preservadas. La composición canónica `state/visual-scan-release/release.compose.json` apunta a c9d7a78. Evidencia de despliegue: `state/browser-text-release-20261117/live-checks.json`. También se guardó **backups/browser-text-first20-20261117.dump** después de las tres revisiones reales; ese segundo dump no se restauró de nuevo. No sobrescribir la base personal para ensayarlo.

## Antecedentes de comprobación · c9d7a78 / 0022

Estos pases históricos no certifican WXT 0.6.0 ni 0023. Dos pases anteriores sobre c9d7a78 limpio: focalizado **c0bcc46c8b** (69 Pytest, 43 Vitest, 2 Playwright, 15 WXT) e integral **5a5761c626** (366 Pytest, 43 Vitest, 41 Playwright, 15 WXT; un canvas móvil omitido). Build, salud/OpenAPI, Alembic y limpieza aprobados; instalación personal y volúmenes intactos durante las pruebas. Herramientas: 23 pruebas aprobadas. Los fallos previos y sus correcciones están en [TESTING](TESTING.md). [CI del código aprobada](https://github.com/ARVI17/emuladordcp26/actions/runs/44081146919), comprobada después de la carga personal.

Aceptación personal: lecturas 1, 2 y 3 revisadas desde la UI, 20 copias en cada una, nombres/medias/posiciones contrastados con la lista visible, seis atributos por carta, mismos IDs y ningún histórico modificado. La comprobación privada posterior usó una transacción de solo lectura. No se persistieron capturas, credenciales ni inventario en Git. No se certificó el OCR de fichas gráficas reales: sus dos rechazos del 16-nov siguen documentados. Los ensayos de corrección de dos campos y de once más siete protegidos son sintéticos; la principal personal sigue pendiente.

La carga anterior usó Chrome conectado/Playwright para leer elementos visibles y revisión local de texto. No fue sincronización automática ni paginación completa. WXT 0.5.1 conserva sus pruebas y artefacto privado, pero no se cargó en Chrome por el bloqueo del administrador de extensiones. No repetir esa instalación como si habilitara AUTO-1: ese artefacto aún carece de lector EA. No eludir el bloqueo por otra superficie. Cualquier distribución futura debe venir después de un prototipo probado y declarar los permisos nuevos concretos. [Contrato asistido](ASSISTED_READING.md), [carga anterior](REAL_CLUB_FIRST_LOAD.md).

Operación: `powershell -ExecutionPolicy Bypass -File scripts/fc27.ps1 Estado`, `python scripts/project_status.py --check`. Actualizar PROJECT_STATE y regenerar la vista al cerrar cada sprint. No hay agente de fondo que actualice el juicio funcional.
