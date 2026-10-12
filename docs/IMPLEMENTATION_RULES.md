# Invariantes de implementación

Estas reglas forman parte del alcance actual y no deben relajarse incidentalmente:

1. No solicitar, almacenar ni registrar credenciales, cookies, tokens, OAuth o códigos de EA/FC Companion.
2. No afirmar conexión API con el club real. ADB lee/controla visualmente el dispositivo del propietario y puede acumular candidatos revisables, pero no hay API autenticada, scraping autenticado ni sincronización oficial de la cuenta.
3. La automatización asistida puede capturar, inspeccionar, tocar, deslizar y preparar una combinación ya validada. No debe añadir compras, ventas, partidos, login ni la pulsación final de entrega como efecto secundario de una consulta, cálculo o plan.
4. Optimizar un DCP es una simulación sin escrituras. Confirmar debe volver a validar contra el estado actual, requerir una acción explícita del usuario, rechazar cartas protegidas y guardar un snapshot restaurable.
5. Las cartas consumidas o eliminadas usan `Player.deleted`; no convertir estos flujos en borrado físico sin migración, respaldo y autorización clara.
6. Las capturas OCR se procesan en memoria y siempre exigen revisión. No persistir la imagen ni crear cartas automáticamente. `InventoryScan` puede conservar hashes, candidatos y progreso, nunca bytes de imagen ni texto de credenciales.
7. La importación CSV/XLSX primero presenta una vista previa; solo `confirm=true` escribe. Mantener validación de extensión, esquema, tamaño y rangos.
8. No exponer el stack directamente a Internet: no tiene autenticación multiusuario. Una publicación exige primero TLS, autenticación, secretos seguros y firewall.
9. No devolver trazas o detalles internos al cliente. Registrar el error localmente y conservar respuestas públicas genéricas.
10. Mantener CORS restringido, consultas ORM parametrizadas, límites de carga y las cabeceras CSP/`nosniff`/`SAMEORIGIN`/Referrer-Policy.
11. Ollama solo recibe un resumen controlado del inventario, no acceso directo a la base ni capacidad de mutación.
12. La media y la química son aproximaciones locales. No presentarlas como fórmula oficial garantizada de EA.
13. Un plan ADB exige calibración y la frase exacta `PREPARAR <id>` antes de ejecutarse. Justo antes de encolarlo vuelve a validar jugadores/requisitos, presencia del serial, resolución y ausencia de otro plan `queued`/`running` para ese dispositivo. Debe conservar `final_submission_automated=false`, poder cancelarse antes de terminar y generar únicamente pasos previos a la entrega irreversible.
14. Las coordenadas son absolutas para una resolución/pantalla concretas. Un cambio de resolución, orientación, escala o interfaz obliga a recalibrar y revisar manualmente.
15. Una lectura de inventario exige dispositivo/resolución estables, ignora hashes repetidos y limita 50 pantallas/1000 candidatos. Importar hasta 500 cartas exige `IMPORTAR <id>`; archivar solo nombres demo exige `REEMPLAZAR DEMO <id>`.
16. Los requisitos detectados por OCR son un borrador local. Nunca tratarlos como restricciones verificadas hasta revisión humana.
17. `POST /emulator/pair` acepta únicamente código temporal ADB de seis dígitos. Puede usarlo como argumento de proceso, pero nunca persistirlo, devolverlo, incluirlo en errores propios ni auditarlo.

Los estados persistidos de un plan son `draft`, `prepared`, `queued`, `running`, `completed`, `failed` y `cancelled`. `completed` significa únicamente que terminó la colocación prevista; nunca significa que el DCP fue entregado. Las rutas de conexión, toque/deslizamiento manual, calibración y cambios de plan relevantes se auditan; cada paso ejecutado crea un `AuditLog` `execute_step`, y un error crea `execute_failed` además de persistir `last_error`.

## Reglas para modificar el proyecto

### Antes de editar

- Ejecuta `git status --short`; el árbol puede contener cambios del usuario o de otros agentes. No limpies ni reviertas cambios ajenos.
- Lee los archivos de la capa afectada y sus pruebas. No confíes solo en README o documentación.
- Comprueba el OpenAPI real en `/api/openapi.json` cuando cambies rutas.
- Mantén el proyecto local-first y los contenedores propios.

### Backend y datos

- Toda modificación del esquema requiere una nueva revisión Alembic; no edites migraciones ya aplicadas para simular una nueva versión.
- Mantén alineados modelo SQLAlchemy, esquema Pydantic, serialización de ruta, migración, seed y tipos del frontend.
- Usa la sesión inyectada por `get_db`; agrega el evento `record(...)` en la misma transacción para mutaciones relevantes.
- Valida antes de mutar y confirma con `db.commit()` una sola unidad lógica. En DCP, no elimines el snapshot ni la revalidación de confirmación.
- Conserva `Player.deleted.is_(False)` en consultas de inventario disponible.
- Si agregas un requisito DCP, impleméntalo tanto en `solve` como en `validate_solution` y añade pruebas factibles e imposibles.
- Un plan de emulador debe nacer de una solución revalidada, rechazar IDs repetidos/no disponibles/protegidos y guardar un snapshot inmutable de nombres y requisitos usados para construir sus pasos.
- Revalida de nuevo al preparar y al ejecutar. Conserva la resolución de calibración en el snapshot, compárala con `adb shell wm size` antes de encolar y al iniciar la tarea, y no permitas dos planes `queued`/`running` sobre el mismo serial.
- `AppSetting.value` es JSON mutable: conserva las copias `dict(...)` al leer/guardar la configuración de emulador o asigna un objeto nuevo, para que SQLAlchemy detecte y persista la calibración.
- Conserva las validaciones de dirección/serial ADB, coordenadas dentro de la pantalla, texto saneado, teclas permitidas, timeout y tamaño PNG. No expongas una ruta genérica para ejecutar comandos ADB arbitrarios.
- `build_dcp_steps` no debe generar etiquetas ni coordenadas de enviar/entregar; cualquier extensión requiere una prueba que demuestre que sigue deteniéndose antes del submit final.
- Las rutas de `InventoryScan` no deben persistir PNG/texto OCR completo. Conserva el rechazo de capturas repetidas, los topes, las frases diferenciadas y la selección explícita de jugadores.
- Los coeficientes efectivos del optimizador están codificados en `_cost`; el registro `app_settings.optimizer` aún es informativo y no reconfigura el solver. No documentes lo contrario sin conectar ambas capas.
- Los endpoints no llevan `/api` en `routes.py`. Nginx añade ese prefijo externamente y FastAPI usa `root_path="/api"`; `TestClient` llama rutas como `/health` y `/players`.

### FC27, identidad y consumos

- `Profile.game_version` es la edición activa. No conviertas datos FC26 en FC27 por cambiar el texto de la UI; toda mutación valida edición.
- Las reservas `resource_locks` y la recarga dentro de la reserva son obligatorias para mutaciones de inventario. Las garantías entre procesos requieren PostgreSQL.
- La protección efectiva une candado manual y pertenencia a cualquier equipo protegido. Desproteger un equipo no modifica `Player.protected`.
- Cada consumo tiene propietario `consumed_by_submission_id`. Restaurar valida todos los propietarios antes de tocar cartas; un snapshot ambiguo se rechaza.
- Galería es historial local: no elimina adquisiciones al consumir cartas, ignora cesiones y utiliza la carta base de evoluciones. Nunca inventar puntos/umbrales ni recompensas de EA.
- Las evoluciones son simulaciones sobre copia y exigen requisitos revisados. Los topes no deben reducir atributos/roles ya superiores.
- Paquetes de contenido requieren vista previa/hash, validación y recibo por hash. Noticias públicas no alteran requisitos automáticamente.
- Pruebas destructivas de tablas usan exclusivamente `TEST_DATABASE_URL` apuntando a datos desechables; nunca heredes `DATABASE_URL` de una instalación habitual.


## Lecturas visuales adicionales

La observación `/emulator/scans/{id}/observe` es una acción manual de una sola jerarquía: sin temporizador, OCR, Ollama, toque/deslizamiento o mutación ante pantalla/firma repetida. Los resúmenes no incluyen candidatos y la revisión carga como máximo 20 formularios. La carga global admite 5000 pendientes y exige `IMPORTAR TODO EL CLUB`; no hidrata miles de controles. La identidad visual es nombre normalizado + media + posición; comparar también contra eliminadas evita resucitar cartas consumidas. Confirmar DCP retira candidatos de la misma identidad. Los borradores OCR/accesibilidad exigen revisión y las frases `ACTUALIZAR DCP` / `ACTUALIZAR OBJETIVOS`.

Los límites WSL del equipo (5 GB RAM, 2 GB swap) no se reducen sin repetir PostgreSQL/Pytest, Playwright, OCR e inferencia GPU. Ollama es opcional: su caída no bloquea el resto. Los nuevos cálculos y la ayuda determinista no necesitan un LLM.
