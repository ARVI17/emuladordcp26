# Principal y propuestas DCP

La principal se identifica con una selección explícita y `PROTEGER PRINCIPAL <id>`. La migración `0015` no deduce la principal de banderas históricas ni de la plantilla activa en EA. Conserva un snapshot con formación, táctica y plazas; su once, suplentes y reservas generan protecciones persistentes por ID de copia. Un cambio revisado conserva las protecciones anteriores. Las protecciones manuales, favoritos y proyectos Evo siguen siendo independientes.

Crear, comparar o duplicar una alternativa no cambia esa selección. El cálculo para jugar permite usar copias protegidas; `avoid_main` permite excluirlas de una propuesta. Los equipos idénticos se agrupan en la comparación de perfiles. La química sigue sin verificar.

El servidor rechaza consumo, archivo, marca de duplicado utilizado y cambios incidentales de la principal. Las protecciones sobreviven a cuarentena o ausencia remota. Sin principal completa se permite simular, pero se bloquea confirmar un DCP. Los cambios en la principal y la confirmación se serializan con el bloqueo de inventario PostgreSQL.

`/dcp/preferences` conserva filtros por contexto en las preferencias locales; `/dcp/exclusions` pagina las razones de exclusión. Los filtros de media, posición, liga, club, nacionalidad, tipo, transferibilidad, duplicado, precio conocido y ubicación nunca exceptúan protecciones. Un precio desconocido no cumple un precio máximo. Las ubicaciones autorizadas provienen del mapeo de copias; las entradas manuales se identifican como registro local.

La rareza también se filtra. «Conservar transferibles valiosos» excluye transferibles por encima del umbral y aquellos sin precio conocido; no obliga a excluir intransferibles por ese umbral. «Mostrar también variantes pendientes» amplía únicamente la inspección de exclusiones, sin admitirlas al solver. Las recomendaciones de juego ofrecen «No reutilizar mi principal» de forma independiente de los candados de consumo.

Cada solución de `/segments/{id}/optimize` incluye `review_token`. Una selección manual puede revisarse en `/segments/{id}/review`. Confirmar exige ese comprobante firmado y revalida las copias, las reglas, el progreso, el contexto, la entrada, el inventario, las reservas, los filtros y la principal dentro de la misma exclusión transaccional. Caduca a los cinco minutos. El comprobante no acredita una entrega en EA ni autoriza a automatizarla.

Las pruebas usan inventario sintético. El fixture general selecciona expresamente su principal sintética; los tests de límite no lo hacen. Ningún mock de identidad, proveedor o catálogo está habilitado en producción.

La recomendación y los perfiles incluyen una comparación de solo lectura con la principal: encaje de cada puesto equivalente, mejora/pérdida local y coste adicional cero al usar cartas propias. Un puesto sin equivalente queda pendiente, sin atribuirle una ganancia. El cálculo usa el mismo perfil de atributos en ambos lados, recurre a la media cuando faltan atributos y no certifica rendimiento o química oficial. La comparación no cambia la principal ni sus candados.

## Presupuesto y prioridades del conjunto

`/dcp/joint-preview` admite hasta seis segmentos y 24 copias, un límite opcional del valor registrado y un orden explícito de prioridades. Por defecto exige todos los segmentos; la opción de selección parcial permite elegir segmentos completos por ese orden. Completar uno de mayor prioridad prevalece sobre todos los de menor prioridad. Ninguna copia puede aparecer en dos segmentos de la misma solución y cada selección pasa de nuevo por el validador independiente.

El límite es el valor de las cartas propias, no un gasto adicional: las compras propuestas siguen siendo cero. Con límite, los precios desconocidos se excluyen; sin límite se indican como desconocidos y no se suman como cero. Se muestran valor por segmento/conjunto, pendientes y, cuando corresponde, aportación, sobrante y puntuación restante. Las protecciones y reservas no pueden exceptuarse mediante presupuesto, prioridad ni parámetros adicionales. Un timeout no demuestra inviabilidad. Esta ruta simula bajo el bloqueo del inventario, no consume ni sustituye la revisión firmada necesaria para confirmar cada DCP.
