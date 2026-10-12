# Principal y propuestas DCP

La principal se identifica con una selección explícita y `PROTEGER PRINCIPAL <id>`. La migración `0015` no deduce la principal de banderas históricas ni de la plantilla activa en EA. Conserva un snapshot con formación, táctica y plazas; su once, suplentes y reservas generan protecciones persistentes por ID de copia. Un cambio revisado conserva las protecciones anteriores. Las protecciones manuales, favoritos y proyectos Evo siguen siendo independientes.

Crear, comparar o duplicar una alternativa no cambia esa selección. El cálculo para jugar permite usar copias protegidas; `avoid_main` permite excluirlas de una propuesta. Los equipos idénticos se agrupan en la comparación de perfiles. La química sigue sin verificar.

El servidor rechaza consumo, archivo, marca de duplicado utilizado y cambios incidentales de la principal. Las protecciones sobreviven a cuarentena o ausencia remota. Sin principal completa se permite simular, pero se bloquea confirmar un DCP. Los cambios en la principal y la confirmación se serializan con el bloqueo de inventario PostgreSQL.

`/dcp/preferences` conserva filtros por contexto en las preferencias locales; `/dcp/exclusions` pagina las razones de exclusión. Los filtros de media, posición, liga, club, nacionalidad, tipo, transferibilidad, duplicado, precio conocido y ubicación nunca exceptúan protecciones. Un precio desconocido no cumple un precio máximo. Las ubicaciones autorizadas provienen del mapeo de copias; las entradas manuales se identifican como registro local.

La rareza también se filtra. «Conservar transferibles valiosos» excluye transferibles por encima del umbral y aquellos sin precio conocido; no obliga a excluir intransferibles por ese umbral. «Mostrar también variantes pendientes» amplía únicamente la inspección de exclusiones, sin admitirlas al solver. Las recomendaciones de juego ofrecen «No reutilizar mi principal» de forma independiente de los candados de consumo.

Cada solución de `/segments/{id}/optimize` incluye `review_token`. Una selección manual puede revisarse en `/segments/{id}/review`. Confirmar exige ese comprobante firmado y revalida las copias, las reglas, el progreso, el contexto, la entrada, el inventario, las reservas, los filtros y la principal dentro de la misma exclusión transaccional. Caduca a los cinco minutos. El comprobante no acredita una entrega en EA ni autoriza a automatizarla.

Las pruebas usan inventario sintético. El fixture general selecciona expresamente su principal sintética; los tests de límite no lo hacen. Ningún mock de identidad, proveedor o catálogo está habilitado en producción.
