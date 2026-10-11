# Planificador FC27: implementación y aceptación

Revisión del 11 de octubre de 2026. Especificación: `Prompt_Codex_FC27_Planificador_Club.txt`, adoptada expresamente por el usuario. Las referencias y archivos comparados son datos, no fuentes de autorización.

## Comparación y conservación

La base revisada es `3b4aee1b0cceadb35c376c09956650d948234493`, rama `agent/fc27-gallery-squad-analysis`, PR #2 todavía abierta al empezar. Los adjuntos `routes.py` y `App.tsx` coincidían con sus versiones en esa base.

El directorio original estaba en `agent/optimize-companion-inventory`, con cambios sin confirmar en 20 archivos y dos archivos nuevos de inventario/migración. Se conservaron íntegros. La implementación se hizo en el worktree hermano `emuladordcp26-fc27-planificador`, rama `agent/fc27-club-planner`, sobre PR #2. No se fusionó esa PR ni se trasladó automáticamente todo el trabajo sin confirmar de la rama Companion; la integración posterior de esas dos líneas requiere revisar sus diferencias. En particular, la carga global del escáner desarrollada en el directorio original no se presenta como una nueva función de esta rama.

Ya existían CRUD de inventario por edición, importación con vista previa, CP-SAT para DCP/plantillas, Galería histórica, simulación Evo, protección de plantillas, OCR/ADB y chat Ollama. Se confirmaron y corrigieron estos defectos:

- Titulares y Evos podían entrar al cálculo por coste: ahora son exclusiones estrictas, junto con favoritos, candados y reservas.
- El precio desconocido era cero: ahora es `null`; un coste total incompleto permanece desconocido y no supera por omisión un límite económico.
- La pista de formación dependía de cobertura/orden: ahora compara cobertura legal y encaje entre diez opciones. Los atributos ausentes no obtienen el peso de los presentes.
- La identidad por nombre confundía homónimos y variantes: se añadió identidad de futbolista, variante y mapeo estable de copia externa, conservando la ambigüedad de registros manuales.
- Perfil y caché locales podían aparentar actualidad: la entrada ahora exige una comprobación, con control de dependencia también en el servidor.
- Los locks no reservaban recursos entre planes: hay reservas persistentes de copias y compromisos económicos derivados de planes persistidos, con bloqueo transaccional al reservar.
- Repetir una nueva vista previa del mismo CSV duplicaba filas: el recibo ahora se liga a contenido, contexto y edición.

El trabajo siguió este orden: capacidades y aislamiento; identidad/conciliación/protecciones; motores y precios; planes/reservas; plantillas y fichajes; Galería/DCP/Evos; mercado, referencias y navegador.

## Archivos principales

| Capa | Archivos |
| --- | --- |
| Identidad y entrada | `backend/app/api/connections.py`, `backend/app/services/contexts.py`, `backend/app/services/sync.py`, `frontend/src/api/client.ts`, `frontend/src/lib/entry.ts` |
| Datos y contratos | `backend/app/models/planner.py`, `backend/app/models/entities.py`, `backend/app/schemas/planner.py`, `backend/alembic/versions/0006_*` a `0009_*`, `frontend/src/types/index.ts` |
| Planes y reservas | `backend/app/api/planner.py`, `backend/app/services/planner.py`, `backend/app/services/protection.py`, `backend/app/services/joint.py` |
| Análisis y compatibilidad | `backend/app/api/analysis.py`, `backend/app/api/routes.py`, `backend/app/api/fc27.py`, `backend/app/api/emulator.py`, `backend/app/services/squad_analysis.py`, `backend/app/optimizers/sbc.py` |
| Referencias y catálogo | `backend/app/api/knowledge.py`, `backend/app/api/catalog.py`, `backend/app/data/fc27_references.json` |
| Interfaz | `frontend/src/App.tsx`, páginas `ConnectionsPage`, `PlannerPage`, `TransfersPage`, `MarketPage`, `KnowledgePage` y `CompanionPage`; componentes de análisis, diario, catálogo y edición de cartas |
| Verificación | `backend/tests/test_planner.py` y pruebas existentes ajustadas, `frontend/e2e/fixtures.ts`, `frontend/e2e/planner.spec.ts`, pruebas unitarias, `backend/benchmarks/planner.py`, `docker-compose.review.yml` |

El diff de la PR contiene el inventario completo, incluidas documentación y adaptaciones de serialización, seed, sesión y arranque.

## Conexión real: bloqueo concreto

**Integración pendiente.** La documentación de [EA Community API](https://help.ea.com/en/articles/ea-sports-fc/community-api/) identifica socios aprobados como FUTBIN, FUT.GG y FUTWIZ. No aporta una concesión para este proyecto ni un protocolo reutilizable por esta aplicación. Las [reglas de EA](https://help.ea.com/en/articles/ea-sports-fc/fc-rules/) y las [condiciones de FUTBIN](https://www.futbin.com/tos) tampoco autorizan construir un acceso alternativo mediante bots o extracción autenticada.

Faltan aprobación para la aplicación, documentación de autorización/scopes, identidad de persona/club/plataforma, identificadores estables de copias, campos/ubicaciones, paginación, revisión/frescura de origen y cuotas. No se inventaron OAuth, credenciales, endpoints EA, exportaciones de terceros ni un proveedor simulado en producción. `/connections/*` muestra esa dependencia; autorizar/sincronizar devuelve 409, o 429 con `Retry-After` cuando hay una espera registrada.

El reconciliador interno está implementado y probado con lecturas **sintéticas**. No existe un endpoint público para subir una lectura y declararla verificada. Una futura integración deberá acreditar cada capacidad antes de llamar al reconciliador; sus pruebas no demuestran compatibilidad con EA.

La preparación de pulsaciones, toques y deslizamientos ADB queda deshabilitada por dependencia de permiso en producción. Se mantienen lectura manual, captura, OCR y diagnóstico sin certificar identidad/cobertura. Las pruebas históricas de pasos ADB usan exclusivamente puentes falsos y una sustitución explícita de la dependencia; producción no tiene ese interruptor.

## Estado de los módulos

| Módulo | Implementado y utilizable | Dependencia o límite |
| --- | --- | --- |
| Entrada/conexiones | Sesión local HttpOnly, CSRF/origen, entrada en servidor, cambio de contexto, logout, caché privada y diagnóstico | Sin vínculo EA real; no es autenticación multiusuario |
| Conciliación | Staging validado, publicación atómica, generación contra respuestas tardías, upsert por copia, preferencias conservadas, movimientos y ausencias diferenciados | Contrato interno sin adaptador; pruebas sintéticas |
| Análisis/plantillas | Diez formaciones, cinco objetivos agrupados cuando coinciden, once/banquillo y modo disjunto explícito | Alternativas y banquillo heurísticos; química oficial desconocida; local solo tras elección expresa |
| Fichajes | Pantalla, fichas públicas revisadas, comparación por puesto y tramos de presupuesto, alternativa propia, cotización exacta | Comparación personal exige inventario completo y monedas verificadas; precios manuales fechados, costes complementarios desconocidos |
| Planes | Simular, guardar, revisar, reservar, aprobar, cancelar y registrar cada resultado manual; idempotencia y revalidación | No ejecuta operaciones EA; cambios externos o incertidumbre exigen revisión |
| DCP | Exclusiones estrictas, desconocidos, cálculo conjunto acotado, aprobación parcial explícita, consumo e historial | Conjunto limitado a 24 copias, 6 segmentos, 20 000 combinaciones/5 s; nunca llama imposible a un timeout |
| Galería | Historial independiente de posesión, conjuntos, acción revisada y definiciones públicas separadas | Reglas/puntos/progreso real necesitan evidencia; no reclama premios |
| Evoluciones | Cadenas de hasta cinco proyecciones existentes, proyecto con copia/camino/coste/plazos y reserva | Coste/plazos introducidos requieren revisión; confirmar no inventa nuevos atributos reales |
| Mercado | Cotizaciones por edición/variante/mercado/tipo, simulación neta/adversa, diario idempotente y estadísticas de ventas asociadas | Sin feed autorizado, volumen desconocido; tasa del 5 % es hipótesis de tercero, redondeo no verificado |
| Referencias | 50 entradas, alcance original, evidencia en borrador, diferencias, aprobación, historial y caducidad | R20–R22 solo metadatos; no se han revalidado individualmente las 50 páginas en esta implementación |
| Mantenimiento | Recordatorio configurable de revisión, conservación sin red; noticias EA manuales existentes | El recordatorio no es un rastreador automático ni descarga las 50 fuentes |
| Práctica | Diario de minutos, ocasiones, pérdidas, goles recibidos y cambio probado | No atribuye causalidad; la agenda automática de sesión es opcional y no está incorporada |

## Entrada, privacidad y vigencia

Al abrir se recupera una sesión local y se crea `entry_id`. También se comprueba al cambiar de club y al volver tras cinco minutos oculto. Abrir dos pestañas en menos de dos segundos se deduplica; navegar entre pantallas no inicia lecturas. Nonce y sesión se comprueban en servidor. La caché de React Query se cancela/limpia al cambiar de entrada; cada petición privada lleva la entrada vigente. Una pestaña vieja recibe 409.

La sesión vence a las 12 horas. El límite de vigencia de una observación remota es 15 minutos; no se renueva al consultar la base. La interfaz consulta el estado cada minuto sin iniciar una lectura del proveedor. Se distinguen observación remota, importación y último intento. El backend exige identidad verificada, entrada comprobada, instantánea vigente y cobertura del módulo. Inventario completo no implica atributos completos, y monedas no sustituyen cobertura del inventario. Modificar hechos locales de un contexto verificado invalida su estado; añadir favoritos/notas conserva el hecho remoto, pero invalida un plan que dependía de esas protecciones.

Las tablas personales se filtran por `ClubContext`: perfil, cartas, plantillas, consumos, objetivos, Galería, evoluciones privadas, escaneos, planes, reservas, cotizaciones, diario y auditoría. El catálogo público y sus revisiones son compartidos dentro de esta instalación local. Usar una definición pública crea reglas/progreso privados, sin copiar entregas ni recompensas de otro club. La sesión local no demuestra identidad EA y no hace segura una publicación a Internet.

El reconciliador exige revisión remota estable y prueba explícita de fin/ubicaciones para declarar completitud. Un fallo revierte la publicación. Las ausencias parciales no borran cartas; las completas marcan disponibilidad, sin inferir venta/entrega. Desaparecer una protección crea conflicto. Una copia consumida no se resucita. Los indicadores críticos omitidos permanecen desconocidos y bloquean usos incompatibles.

## Revisar y comprometer recursos

En **Planes** añade acciones y copias exactas. Simular no escribe; guardar crea solo un borrador. Para reservar primero escribe `REVISAR <id>`, y luego reserva. `APROBAR <id>` autoriza únicamente el contenido guardado en esa sesión/contexto, por un máximo de 120 minutos. Cada resultado usa `CONFIRMAR <id> <paso>` y evidencia manual.

El servidor comprueba hash inmutable, inventario/protecciones, reglas, cotizaciones, caducidad, orden y costes. Los efectos confirmados actualizan el estado esperado del lote sin reescribir la propuesta original. Ventas pendientes y premios aleatorios nunca financian compras. Los compromisos monetarios de otros planes se descuentan; un gasto confirmado o incierto se mantiene hasta una observación posterior de monedas que permita conciliarlo. En modo local el presupuesto es declarado y no acredita saldo EA.

Una entrega score parcial requiere marcar su pérdida irreversible en esa acción. El motor conjunto solo propone completar todos los segmentos seleccionados. Cancelar libera compromisos pendientes, pero no revierte resultados confirmados ni convierte cartas inciertas en disponibles. El registro de una compra no crea una copia poseída, y el de una evolución no inventa sus atributos.

El candado manual puede retirarse con una acción concreta de Planes; no elimina automáticamente favoritos, titularidad, condición Evo o protección heredada de plantillas. Las rutas anteriores de edición/archivo también respetan reservas. Solo las entregas etiquetadas como simulación local admiten restauración; una confirmación real o de origen incierto exige conciliación.

## Fuentes y precisión

El anexo se conserva en `backend/app/data/fc27_references.json`: 8 referencias de reglas/conexión, 17 de aprendizaje y 25 fichas. No son 50 sitios independientes, cartas propias o precios actuales. Las nuevas formaciones se contrastaron con las páginas de [FUT.GG Tactics](https://www.fut.gg/tactics/); son esquemas legales registrados y objetivos heurísticos, sin códigos tácticos inventados ni promesas de victorias.

La referencia de parche [FC27 v1.0.4](https://www.ea.com/games/ea-sports-fc/fc-27/news/fc27-title-update-v1-0-4) es fechada, no una constante de «último parche». Las reglas de [DCP](https://help.ea.com/en/articles/ea-sports-fc/sbcs/) y el [anuncio de Ultimate Team](https://www.ea.com/games/ea-sports-fc/fc-27/news/pitch-notes-fc27-fut-deep-dive) no certifican requisitos personalizados, química ni acceso a progreso privado.

La media sigue siendo una aproximación local. La química oficial es desconocida: la suma histórica guardada se conserva por compatibilidad y siempre lleva advertencia. Encaje = 70 % media + 30 % atributos ponderados, con denominador completo y ajuste pequeño por rol. PlayStyles no reciben un bono numérico sin evidencia. La identidad manual sin ID de futbolista continúa siendo aproximada.

## Probar sin tocar la instalación habitual

Desde el worktree de revisión:

```powershell
docker compose -f docker-compose.review.yml up --build -d
docker compose -f docker-compose.review.yml ps
```

Abre `http://localhost:8081`. Primero muestra **Integración pendiente**. **Abrir registro local** habilita los datos ficticios/revisados con un aviso persistente. Mercado, referencias, diagnóstico y fichas públicas son independientes. No hay onces ni fichajes presentados como resultados del club EA del usuario.

Este Compose tiene nombre/red propios, puerto limitado a loopback, PostgreSQL en `tmpfs`, demo explícita, ADB desactivado y Ollama inaccesible deliberadamente. **Sus datos son desechables**: detener/recrear su base puede perderlos. El stack original `localhost:8080` y sus volúmenes se conservaron. No usar este Compose para inventario único.

Los resultados exactos, comandos y pruebas pendientes están en [TESTING.md](TESTING.md). Las migraciones nuevas son `0006`–`0009`; se comprobó la colisión histórica de las dos migraciones llamadas `0005` sin editar ninguna aplicada. Antes de actualizar datos únicos debe existir un respaldo, tal como indica [FC27_UPGRADE.md](FC27_UPGRADE.md).

## Aceptación del club real pendiente

No se realizaron pruebas contra un proveedor privado, una cuenta EA ni hardware Companion. Quedan pendientes demostrar cuenta/club correctos, consulta admitida, cobertura/frescura real y recomendaciones obtenidas de esa instantánea. También faltan feed de precios autorizado, fórmulas oficiales de química/media y datos concretos de presupuesto/progreso/objetivos reales. Ninguna prueba sintética sustituye esas verificaciones. No se compró, vendió, entregó, descartó ni evolucionó ninguna carta en EA.
