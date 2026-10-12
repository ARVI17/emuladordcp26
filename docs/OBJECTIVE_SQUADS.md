# Plantillas para objetivos FC27

Centro FC permite elegir hasta seis objetivos y abrir Plantillas → Para objetivos. Una transcripción revisada conserva fuente, fecha, texto original, condiciones normalizadas, acciones de partido, modalidad, dificultad mínima, cesiones, dependencias, repetibilidad y vencimiento. Es una hipótesis auxiliar manual: no certifica un objetivo activo de EA. No existe lectura de progreso remoto en producción.

## Composición y contexto

`schemas/objective_planning.py` valida cantidades mínimas, máximas y exactas por liga, club, nacionalidad, tipo, media, posición, rareza y condición especial. Cada condición tiene ID y texto propio; hereda la fuente y fecha de la revisión del objetivo. Once, banquillo y convocatoria se cuentan por separado. La posición del once es el puesto asignado; en banquillo se usa la posición principal registrada. Participantes del partido y texto no interpretado quedan pendientes.

`services/objective_squads.py` utiliza CP-SAT y un validador independiente. El mínimo exige suficientes coincidencias conocidas; el máximo incluye también las coincidencias posibles con metadatos desconocidos. No se toma un indicador omitido como falso. Se comprueban copia única, identidad del futbolista, posiciones, disponibilidad y cesiones. Las reservas incompatibles se excluyen; la protección de la principal no impide jugar con ella en otra propuesta. «Sin principal» necesita una principal completa y revisada.

Las alternativas son composición propia, mejor encaje local sin compras y, cuando puede acreditarse, una alternativa sin principal. Resultados idénticos se agrupan. Todas usan copias propias con coste adicional cero. El catálogo actual no ofrece candidatas de compra con todos los metadatos/cesión acreditados: no se inventa un fichaje mínimo ni una carencia a partir de datos parciales. Las propuestas no garantizan química, resultados o victorias.

Modalidades incompatibles producen sesiones separadas; no se suman progresos. Dentro de una modalidad se toma la dificultad mínima más exigente conocida y se avisa de datos pendientes. Dependencias, vencimientos desconocidos y partidos restantes de cesión no disponibles se muestran expresamente. Cuando una restricción exige partidos restantes, se excluyen las cesiones por falta de ese dominio.

## Guardado, exportación y progreso

Las rutas `/objective-planning`, `/preview`, `/save`, `/export` y `/{id}/progress` distinguen lectura, cálculo y escritura. Las reglas auxiliares se guardan con `REVISAR OBJETIVO`. Su acceso a una simulación no levanta la cuarentena documental de DCP, Galería u otros módulos. La migración `0016` añade reglas, revisión, últimas veinte revisiones y evidencia de progreso sin modificar contadores históricos.

La propuesta firmada dura como máximo cinco minutos o hasta el vencimiento más próximo. Liga contexto/entrada/snapshot/revisión, inventario, reglas/progreso/dependencias, reservas, principal y copias seleccionadas. Guardar y exportar vuelven a validar bajo el bloqueo de inventario. Cambiar un dato relevante exige recalcular; no se guarda ni exporta una propuesta vencida. Un timeout no demuestra inviabilidad.

Guardar crea un squad_id nuevo y un nombre distinguible. `Squad.objective_context` conserva IDs de objetivos, revisiones, fecha y snapshot del guardado como observación histórica; Plantillas permite volver al generador para recalcularla. La protección adicional es opcional; no quita candados, no cambia la principal ni activa una plantilla en EA. Un registro de auditoría impide duplicar el mismo guardado concurrente. Exportar devuelve una lista JSON local. Ninguna de estas acciones modifica progreso.

El contador empieza en `null` si no hay evidencia. Un cero solo se muestra cuando se declaró explícitamente. `REGISTRAR PROGRESO MANUAL` conserva valor, fecha y nota, con origen manual visible; dejarlo vacío vuelve a desconocido. Los contadores históricos se conservan en la base y no se presentan como observados. «Composición lista» no significa objetivo completado, acciones de partido realizadas o premios reclamados.
