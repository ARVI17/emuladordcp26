# Guía de trabajo · Club Lab FC27

Lee [docs/PROJECT_MAP.md](docs/PROJECT_MAP.md) y el código/pruebas de la capa afectada antes de cambiar datos, arquitectura o contratos. Las [invariantes detalladas](docs/IMPLEMENTATION_RULES.md) mantienen las protecciones de importación, ADB, OCR, consumos y restauración.

## Estado y alcance

- Aplicación personal local no oficial: React/FastAPI/PostgreSQL/OR-Tools, Ollama opcional. Solo FC27 en UI y rutas públicas; FC26 histórico permanece aislado, sin borrar ni reconvertir.
- Principal Compose `emuladordcp26`, entrada personal `http://localhost:8090` (predeterminado de Compose: 8080), volumen `emuladordcp26_postgres_data`. `scripts/fc27.ps1 Estado` acredita el puerto efectivo. Conservar imágenes, volúmenes y proyectos ajenos. La revisión antigua de 8081 fue respaldada y retirada; no volver a dejar otra aplicación permanente.
- Cero adaptadores de producción en `ADAPTERS`. [Cuenta y bloqueos](docs/ACCOUNT_ACCESS.md), [contrato del lector](docs/PROVIDER_CONTRACT.md). No pedir credenciales/cookies/tokens EA, inventar protocolos ni abrir una carga pública de snapshots verificados. Abrir EA no conecta esta aplicación.
- La sesión es local (cookie HttpOnly, CSRF, entrada/contexto); el modo local se elige expresamente y el servidor conserva esa elección al recargar. El contexto 1 nunca se asigna automáticamente a una cuenta.
- Migración `0018`: concesiones de extensión y recibos DOM; `0017`: sesiones, lecturas y copias visuales; [flujo asistido y contratos](docs/ASSISTED_READING.md). `0016`: reglas auxiliares de objetivos y evidencia de progreso; `0015` conserva la principal explícita y protegida. [Protecciones y filtros](docs/SQUAD_SAFETY.md). No inferir principal por nombre, media u orden. Guardar alternativas no modifica ni activa la principal en EA.
- `extension/` usa MV3/WXT y un contrato de muestra/exportación propia. No hay selectores EA contrastados. Preserva cola privada, ID/hash/secuencia/fecha, recibo inmutable, revisión por lote y revocación. Galería v2 es optativa; no conviertas puntos fijos v1 en porcentajes. El diario de objetivos declara tareas, nunca incrementa progreso EA.
- Extensión 0.3.0: [reconocimiento guiado](docs/VIEW_RECOGNITION.md), mapas privados acotados y propuestas `proposed`. `profile-extraction.ts` añade definiciones editables/importables y ciclo de prueba/contraste/activación para vista previa manual, aún sin ingesta EA ni transiciones. Cada edición invalida pruebas; un JSON importado no acredita contraste. El inspector funciona sin backend; emparejar/leer muestras comprueba builds y `/reader/capabilities`. Conservar destinos existentes y exigir confirmación al cambiarlos. Un mapa observado no acredita un extractor contrastado.
- [Plantillas para objetivos](docs/OBJECTIVE_SQUADS.md): una transcripción revisada puede alimentar una hipótesis de composición no consumptiva, siempre etiquetada manual; no certifica objetivo activo ni progreso. Guardar/exportar revalidan el comprobante y no incrementan contadores.
- Lectura asistida: captura web voluntaria, OCR deliberado sin imágenes persistidas, contextos separados y admisión SQL de copias revisadas. Una etiqueta de origen nunca basta para admitir propiedad. La guía manual de objetivos no ejecuta EA; sus resultados inciertos bloquean repeticiones incluso tras cancelar.
- Evidencia visual revisada/documental/manual/lectura remota son distintas. El catálogo público no acredita posesión. Los borradores de reglas no se vuelven oficiales por marcar revisión. No activar fixtures sintéticos en producción.

## Operación canónica

```powershell
powershell -ExecutionPolicy Bypass -File scripts/fc27.ps1 Estado
powershell -ExecutionPolicy Bypass -File scripts/fc27.ps1 Inicio
python scripts/verify_docker.py --scope full
```

`Inicio` valida y arranca los contenedores existentes por ID: no reconstruye, recrea ni migra. `Parada` los detiene sin borrar. No usar el Compose de un worktree antiguo para actualizar la instalación personal. El despliegue requiere permiso aplicable, destino acreditado, respaldo restaurado aparte e imágenes/código de recuperación preparados; un push no autoriza merge.

Para probar usa el verificador, no Pytest contra la base habitual. Crea un proyecto temporal con bloqueo entre procesos, etiquetas de propiedad, imágenes únicas, PostgreSQL tmpfs y cierre en `finally`. Recupera restos de una caída solo tras validar manifiestos/IDs/montajes. Nunca borrar volúmenes o imágenes para limpiar. [Flujo](docs/DEVELOPMENT_WORKFLOW.md).

## Reglas de trabajo

1. Un agente, sprints de 1–3 objetivos. Ejecutar `git status --short`, revisar ramas/worktrees/PR y conservar cambios ajenos. No reiniciar diagnósticos o investigar 50 fuentes sin necesidad.
2. Código → pruebas pertinentes → Docker aislado → diff/secretos → commit → push a la rama → SHA remoto. PR en borrador, sin merge automático. Comprobar códigos de salida nativos; PowerShell no los convierte siempre en excepciones.
3. Prohibidos `prune`, `down -v`, `rm -v`, `make reset`, `git reset --hard`, `git clean -fd` y force push. Operar recursos Docker por identidad completa y alcance verificado.
4. `.env`, dumps, inventarios, sesiones, capturas privadas, modelos, `node_modules`, `dist` y bases de pruebas no van a Git. Configuración nueva en `.env.example`; respaldo en `backups/`, evidencia local en `state/` ignorado.
5. Cambios de esquema llevan una nueva revisión Alembic; no editar revisiones aplicadas. Alinear modelo, Pydantic, serialización, migración, seed y TypeScript. El arranque normal no carga demo.
6. Mantener `ClubScoped`, edición, vigencia y admisión ORM en conteos, alias y relaciones. No quitar filtros para recuperar pendientes. La revisión auxiliar conserva su procedencia y límites.
7. Mutaciones relevantes usan sesión `get_db`, bloqueo `resource_locks`, recarga/validación y auditoría en una transacción. No leer atributos ORM expirados dentro de `do_orm_execute`; guardar banderas de contexto en `db.info` al vincular la petición. Conservar JSON por copia/asignación nueva para que SQLAlchemy detecte cambios.
8. Principal, banquillo/reservas, favoritos, candados, Evos y compromisos incompatibles se excluyen de consumo/venta/archivo. Otra copia se evalúa por su ID. Jugar es no consumptivo y puede reutilizar protegidas. No quitar protecciones para lograr una solución.
9. DCP: simulación sin escrituras; confirmación explícita con revalidación de cuenta, snapshot, reglas, disponibilidad, reservas y principal dentro del bloqueo. Mantener snapshot restaurable, baja lógica y propietario del consumo. Restaurar localmente no revierte EA.
10. Un requisito se implementa en solver y validador independiente, con casos viable/imposible. Química/media/encaje locales se presentan con sus límites; `_cost` sigue siendo la configuración efectiva del solver.
11. Galería conserva historial, excluye cesiones y usa base acreditada de Evos; no inventar puntos, premios o progreso. Las simulaciones y exportaciones no incrementan objetivos.
12. Ollama recibe un resumen controlado, nunca acceso a la base o capacidad de mutación; texto factual de chat procede del servidor. Cálculos en motores deterministas, sin LLM por render.
13. ADB apagado por defecto y permisos/compatibilidad pendientes. No comprar, vender, jugar, iniciar sesión ni pulsar entrega final. Mantener calibración, serial/resolución, cancelación y frases exactas descritas en las invariantes.
14. CSV/XLSX: vista previa y confirmación; OCR en memoria y revisión. No persistir capturas o credenciales ni crear cartas automáticamente. No resucitar consumidas por una lectura antigua.
15. No exponer a Internet sin autenticación, TLS, secretos y firewall. Mantener CORS restringido, límites, consultas parametrizadas y cabeceras de seguridad. Errores públicos genéricos y en español, sin trazas ni valores privados.

## Interfaz y contratos

Hash routes en `lib/navigation.ts`; barra lateral, menú móvil y ayuda contextual en componentes propios. [Interfaz](docs/INTERFACE.md). Conservar Atrás/Adelante/recarga y foco. Cabecera desde `/dashboard.account`, nunca desde saldo o nombre del perfil manual. `null` no equivale a cero. Idioma `es-CO`, zona configurable (inicial `America/Bogota`), instantes UTC.

Usar `api()` sin imponer JSON a `FormData`; invalidar todas las claves TanStack afectadas. Datos del dominio en PostgreSQL, preferencias visuales en navegador. Endpoints internos sin `/api`; el proxy público añade ese prefijo. Verificar `/api/openapi.json` real al cambiar contratos. Mantener navegación móvil a ~390 px, sin miles de formularios de inventario.

## Verificación y entrega

- Backend: Pytest completo, salud y OpenAPI sobre PostgreSQL aislado. Migraciones: upgrade/current/check y conservación de datos de una copia.
- Frontend/tipos: Vitest y build. Navegación/layout: Playwright móvil/escritorio sobre Nginx y revisión de capturas reales.
- Docker/Nginx: configuración, arranque detenido, salud externa y degradación sin Ollama; probar cierre tras éxito/fallo/cancelación/caída sin tocar principal.
- ADB/OCR: pruebas pertinentes y ausencia de dispositivo primero; hardware solo con permiso y pantalla/datos desechables sin acciones irreversibles.
- Backup/restore: ensayo separado y copia previa; nunca usar datos únicos como primera prueba.

Resultados vigentes en [docs/TESTING.md](docs/TESTING.md). Reportar lo ejecutado, omitido y fallido, árbol Git, SHA probado/servido y bloqueos concretos. No declarar conectada la cuenta real por una UI, fixture o enlace externo.
