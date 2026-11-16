# Estado y rumbo del proyecto

<!-- Generado por scripts/project_status.py --render-plan; editar PROJECT_STATE.json. -->

Revisión humana: **2026-11-16**. Sprint: Revalidación documental, caducidad por fuente y preparación del club real.

Construir una plantilla competitiva con las cartas reales del propietario y un presupuesto sostenible. Lectura del club, DCP, ventas propuestas, fichajes, Galería y Evoluciones sirven a esa prioridad; ninguna recomendación garantiza victorias ni ejecuta operaciones en EA.

**Siguiente paso:** Aceptar 20 cartas reales mediante captura voluntaria en localhost:8090, corregir dos lecturas y reescanear sin duplicar; proteger once y siete suplentes y comparar al menos tres alternativas. Seguir docs/REAL_CLUB_FIRST_LOAD.md. La revisión pública vence el 16-dic-2026 a las 22:10:56 UTC; no renovarla sin contraste.

Disponible significa código existente; la validación con el club real se registra por separado. Estos estados no se convierten en completos por pasar pruebas sintéticas.

| Hito | Implementación | Club real | Falta |
| --- | --- | --- | --- |
| MEM-1 · Memoria y continuidad | Disponible | No aplica | Revisar criterios y siguiente acción en cada sprint; el diagnóstico no decide que el producto esté terminado. |
| KNOW-1 · Vigencia de formaciones y contenido | Disponible | Contrastado | Fuentes contrastadas el 16-nov y desplegadas en 96a8d21/0022: 11 identificadores de formación, 20 variantes y 27 referencias documentadas. Cinco variantes pendientes, incluidas R33/R49 por presentación holográfica. Revisión hasta 16-dic 22:10:56 UTC; sin renovación automática. Pases corregidos focalizado/integral y CI aprobados; no acreditan el club real. |
| DATA-1 · Club real revisado | Parcial | Pendiente | Cero cartas FC27 activas al auditar. OCR con filas sintéticas; falta contrastar fichas reales. |
| DATA-2 · Identidad de variantes y copias | Parcial | Pendiente | Agrupación provisional entre páginas; falta correspondencia canónica robusta para fichas gráficas y resolución de copias. |
| TEAM-1 · Principal competitiva y alternativas | Parcial | Pendiente | Formaciones revalidadas y cinco perfiles locales disponibles. Falta contrastar el club real, seleccionar/proteger explícitamente la principal y comparar al menos tres alternativas con sus carencias. |
| DCP-1 · DCP activos útiles para el equipo | Parcial | Pendiente | Solver local y lectura manual existen; faltan un tradicional y un simplificado reales, vigencia y compras integradas. |
| PRICE-1 · Precios y presupuesto trazables | Parcial | Pendiente | Cotizaciones manuales existen; importación/conciliación pendientes. Mercado y fichajes están bloqueados en contexto visual por require_module. |
| TRADE-1 · Excedentes y compras para mejorar | Parcial | Pendiente | Comparador por puesto, planes y reservas existen; falta selección transversal de ventas y compras con impacto en el once completo. |
| GALLERY-1 · Galería y Evoluciones | Parcial | Pendiente | Historial, escenarios y rutas locales existen; falta un conjunto real con variantes, reglas, premios reclamados y coste contrastados. |
| ACCEPT-1 · Recorrido personal completo | Pendiente | Pendiente | Falta demostrar el recorrido con el propietario; el pase técnico sintético no lo acredita. |

## Criterios para cerrar cada hito

### MEM-1 · Memoria y continuidad

Dependencias: ninguna.

- Un chat nuevo encuentra visión, avances, evidencia, bloqueos y siguiente acción en los archivos del repositorio.
- El diagnóstico separa HEAD, versión servida y SHA/alcance de pruebas; ausencias se muestran como desconocidas.
- Operación canónica y verificador regeneran el informe privado; CI rechaza estados, dependencias o enlaces inválidos y una vista desactualizada.

Código/evidencia: [scripts/project_status.py](../scripts/project_status.py), [scripts/tests/test_project_status.py](../scripts/tests/test_project_status.py), [docs/MASTER_PROMPT.md](../docs/MASTER_PROMPT.md), [docs/NEXT_SESSION.md](../docs/NEXT_SESSION.md).

### KNOW-1 · Vigencia de formaciones y contenido

Dependencias: ninguna.

- Contrastar formaciones/posiciones y variantes necesarias con fuentes actuales, registrar evidencia y fecha; no renovar automáticamente ni eliminar la guarda.
- Separar en pruebas el reloj de escenarios históricos y el comportamiento real antes/después de caducidad; la fecha del sistema no debe crear falsos pases.
- Validar dos veces las regresiones afectadas y repetir integral; un resultado sintético no acredita vigencia documental.

Código/evidencia: [backend/app/services/squad_analysis.py](../backend/app/services/squad_analysis.py), [backend/app/services/content.py](../backend/app/services/content.py), [backend/app/api/knowledge.py](../backend/app/api/knowledge.py), [backend/tests/test_content_boundary.py](../backend/tests/test_content_boundary.py), [docs/AUDIT_20261116.md](../docs/AUDIT_20261116.md), [backend/app/data/fc27_formations.json](../backend/app/data/fc27_formations.json), [backend/alembic/versions/0022_catalog_review.py](../backend/alembic/versions/0022_catalog_review.py), [backend/tests/test_public_review.py](../backend/tests/test_public_review.py), [docs/SOURCE_REVIEW_20261116.md](../docs/SOURCE_REVIEW_20261116.md).

### DATA-1 · Club real revisado

Dependencias: ninguna.

- Login por el usuario y captura por gesto; pausa, cancelación y salida terminan el flujo sin persistir imágenes o credenciales.
- 20 cartas reales revisadas, dos correcciones y reescaneo idempotente. 8+8 con cuatro repetidas produce 12; copias legítimas siguen separadas.
- Cobertura parcial no elimina cartas ausentes ni revive consumidas; cuenta/contexto y procedencia se conservan.

Código/evidencia: [backend/app/services/visual_scan.py](../backend/app/services/visual_scan.py), [backend/app/services/scan_ocr.py](../backend/app/services/scan_ocr.py), [frontend/src/components/VisualScanner.tsx](../frontend/src/components/VisualScanner.tsx), [backend/tests/test_visual_scan.py](../backend/tests/test_visual_scan.py), [docs/REAL_CLUB_FIRST_LOAD.md](../docs/REAL_CLUB_FIRST_LOAD.md).

### DATA-2 · Identidad de variantes y copias

Dependencias: DATA-1.

- Nombre, media o confianza OCR no certifican por sí solos identidad, posesión, transferibilidad ni versión.
- Distinguir oro base, especiales, holográficas y Evo; ambigüedades exigen revisión y no se admiten por defecto.
- Cada copia conserva su procedencia/contexto; catálogo público y posesión permanecen separados.

Código/evidencia: [backend/app/services/catalog_validation.py](../backend/app/services/catalog_validation.py), [backend/app/services/visual_scan.py](../backend/app/services/visual_scan.py), [docs/OCR_DATA_MODEL.md](../docs/OCR_DATA_MODEL.md).

### TEAM-1 · Principal competitiva y alternativas

Dependencias: KNOW-1, DATA-1, DATA-2.

- Selección explícita de principal, banquillo y reservas; proteger sus copias frente a consumo/venta.
- Comparar al menos tres alternativas con once y siete suplentes, posiciones legales, fijados/excluidos, fortalezas y carencias. Reutilizar protegidas para jugar.
- Guardar alternativa no cambia la principal ni EA. Explicar mejora por puesto y datos faltantes; score local no equivale a probabilidad de victoria.
- Diario de partidos y práctica para evaluar resultados sin atribuir causalidad a muestras pequeñas.

Código/evidencia: [backend/app/services/squad_analysis.py](../backend/app/services/squad_analysis.py), [backend/app/api/analysis.py](../backend/app/api/analysis.py), [backend/app/services/main_squad.py](../backend/app/services/main_squad.py), [frontend/src/components/PlanningAnalysis.tsx](../frontend/src/components/PlanningAnalysis.tsx), [docs/OPTIMIZER.md](../docs/OPTIMIZER.md).

### DCP-1 · DCP activos útiles para el equipo

Dependencias: TEAM-1.

- Requisitos, recompensa, vencimiento y progreso con fuente/fecha. No declarar lista completa sin cobertura.
- Un tradicional y un Streamlined contrastados por solver y validador independiente; casos viable, imposible y datos insuficientes.
- Separar gasto nuevo, valor sacrificado y exceso de Item Score. No llamar gratis a sacrificar cartas valiosas.
- Proteger principal y compromisos; no gastar una copia en dos segmentos. Simular no cambia inventario ni entrega en EA.

Código/evidencia: [backend/app/optimizers/sbc.py](../backend/app/optimizers/sbc.py), [backend/app/services/joint.py](../backend/app/services/joint.py), [backend/app/api/assisted.py](../backend/app/api/assisted.py), [docs/FC27_DCP_RULES.md](../docs/FC27_DCP_RULES.md).

### PRICE-1 · Precios y presupuesto trazables

Dependencias: DATA-2.

- Variante exacta, mercado, moneda, tipo, fuente, fechas y caducidad por cotización; separar PC y PlayStation.
- Desconocido no es cero; histórico no es oferta. Modo local funciona con fuentes caídas y precios manuales/importados permitidos.
- Habilitar planificación visual mediante un contrato explícito de evidencia y presupuesto, sin quitar las protecciones de require_module.
- Saldo observado y presupuesto elegido separados; venta propuesta nunca financia una compra. Ningún adaptador sin autorización aplicable.

Código/evidencia: [backend/app/models/planner.py](../backend/app/models/planner.py), [backend/app/services/planner.py](../backend/app/services/planner.py), [backend/app/services/contexts.py](../backend/app/services/contexts.py), [docs/PRICE_PROVENANCE.md](../docs/PRICE_PROVENANCE.md).

### TRADE-1 · Excedentes y compras para mejorar

Dependencias: TEAM-1, PRICE-1.

- Proponer ventas solo de transferibles disponibles y no protegidos/reservados; valorar cobertura de suplentes, objetivos y Evos.
- Comparar conservar/vender/consumir con neto estimado, reposición, pérdida deportiva e incertidumbre.
- Lista exacta de compras con presupuesto y reserva; ninguna venta pendiente aumenta saldo disponible.
- Solver de propias más compras externas: mínimo comprobado por enumeración pequeña, estado óptimo/factible/desconocido, sin proclamar óptimo global con candidatos incompletos.
- Ninguna simulación compra, vende, entrega ni altera la principal.

Código/evidencia: [backend/app/api/analysis.py](../backend/app/api/analysis.py), [backend/app/services/planner.py](../backend/app/services/planner.py), [backend/app/services/protection.py](../backend/app/services/protection.py), [docs/PRICE_PROVENANCE.md](../docs/PRICE_PROVENANCE.md).

### GALLERY-1 · Galería y Evoluciones

Dependencias: PRICE-1, TEAM-1.

- Separar historial, cartas actuales, elegibilidad, grados y premios; excluir cesiones y usar base acreditada de Evo.
- Un conjunto real compara reutilizar lo adquirido, comprar lo faltante o esperar; no inventar puntos/bonificaciones/recompensas.
- Ruta con flujo de caja, reserva, comisiones parametrizadas y sin reclamar dos veces el mismo premio.
- Comparar Evo con conservar/comprar; declarar tiempo y requisitos pendientes sin aumentar progreso EA.

Código/evidencia: [backend/app/services/gallery_v2.py](../backend/app/services/gallery_v2.py), [backend/app/services/gallery_route.py](../backend/app/services/gallery_route.py), [backend/app/services/evolutions.py](../backend/app/services/evolutions.py).

### ACCEPT-1 · Recorrido personal completo

Dependencias: DCP-1, TRADE-1, GALLERY-1.

- Club revisado → principal protegida → alternativas → DCP/venta/Galería → presupuesto y compras verificables.
- Pruebas aisladas, móvil/escritorio, proveedor caído y cancelación; simulaciones dejan inventario y principal intactos.
- Despliegue con destino acreditado, copia restaurada, recuperación preparada y SHA servido identificado.
- El usuario entiende qué tiene, qué falta, qué conservar y qué hacer ahora; Ollama e integración EA no son requisitos del modo asistido.

Código/evidencia: [docs/MASTER_PROMPT.md](../docs/MASTER_PROMPT.md), [docs/IMPLEMENTATION_STATUS.md](../docs/IMPLEMENTATION_STATUS.md), [scripts/verify_docker.py](../scripts/verify_docker.py).

## Continuar sin perder contexto

- [Prompt maestro](MASTER_PROMPT.md): visión, decisiones y ejecución por sprints.
- [Siguiente sesión](NEXT_SESSION.md): entrega actual y acción concreta.
- [Auditoría del 16 de noviembre](AUDIT_20261116.md): hechos comprobados y límites.
- `python scripts/project_status.py`: genera el informe privado actual en `state/continuity/latest.md`.
- `python scripts/project_status.py --check`: comprueba estructura, dependencias, evidencias y sincronía de esta vista.

El informe privado muestra la hora de observación, Git, Docker y los últimos informes de pruebas. No reemplaza esta revisión humana ni acredita datos EA. No existe un agente de fondo trabajando entre sesiones.
