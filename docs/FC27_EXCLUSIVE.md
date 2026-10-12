# Producto exclusivamente FC27

FC27 es la única edición pública. El nombre técnico del repositorio y sus volúmenes permanece estable. El selector de archivo se retiró; tampoco se pueden consultar otras ediciones mediante parámetros HTTP, contextos, perfil, diario o definiciones públicas.

Las sesiones vinculadas al club aplican límites ORM a consultas, agregados, alias y relaciones. Las escrituras rechazan otras ediciones; la conciliación exige FC27 en el manifiesto y cada copia. Un perfil histórico se conserva y se crea un perfil FC27 vacío, sin trasladar monedas. Las sesiones internas sin contexto quedan reservadas para migraciones, respaldos y fixtures aisladas.

No hay recuperación pública del histórico. Una futura recuperación exige un proceso separado y autorización expresa. No se renombran volúmenes ni se despliega el principal al subir código.

Las pruebas mezclan ediciones exclusivamente en PostgreSQL desechable y comprueban lecturas, agregados, relaciones, mutaciones y preservación de los registros originales.

La verificación de existencia de variantes es un requisito adicional: revisión manual e identidad nominal no equivalen a evidencia de catálogo. Ninguna referencia documental autoriza inventariar cartas.

## Variantes y cuarentena (0013)

`CardVariant` separa la existencia documentada de una variante de la copia declarada por el propietario. Una copia disponible exige edición explícita FC27, ID exacto, nombre, media, posición y tipo coincidentes con evidencia vigente. `documented` acredita una ficha pública; solo `provider_verified` puede acreditar una verificación del proveedor. Ninguno de estos estados demuestra posesión ni inicia sesión en EA.

Se contrastaron las 25 fichas R26–R50: 22 identifican una variante FC27; R26, R31 y R35 quedan pendientes porque sus páginas exactas no fueron accesibles. Las fichas no aportan precios ni completan atributos desconocidos. El catálogo versionado conserva URL, fecha de consulta y vencimiento. Al vencer o revocarse su evidencia, las copias salen de los cálculos sin borrarse. El arranque inserta fichas faltantes y nunca sobrescribe una revisión/revocación existente; renovar evidencia requiere una revisión técnica documentada, sin habilitar una autocertificación por HTTP.

Contratos nuevos:

- `GET /catalog/variants`: búsqueda paginada de referencias vigentes, sin posesión ni precios.
- `GET /inventory/quarantine`: máximo 20 declaraciones pendientes por página, fuera del inventario activo.
- `POST /inventory/quarantine/{id}/review`: frase `REVISAR FC27 <id>`, fuente pública y contraste con el catálogo; conserva favoritos, notas y protecciones. Una URL introducida manualmente no certifica la variante.
- `POST /players`: 201 para copia documentada; 202 para declaración conservada en cuarentena. CSV/XLSX y Companion distinguen `imported` de `quarantined`. Una edición diferente se rechaza; una edición omitida queda pendiente.

La migración 0013 conserva todas las cartas y deja las antiguas pendientes hasta contraste. No convierte el seed ni las referencias en inventario. Galería conserva identidades de variante independientes. Mercado, análisis, DCP, evolución y planificación reciben únicamente copias admitidas por el filtro SQL; una marca `data_reviewed` no lo elude.

Respaldo y recuperación se ensayaron en PostgreSQL desechable: 228 cartas antes/después, 228 entradas de Galería y cuatro planes conservados; dump previo restaurado en otra base con head 0012. El principal no se migró. El rollback utiliza ese respaldo y código compatible; no se ofrece un downgrade que borre evidencia.

## Definiciones y datos heredados (0014)

DCP, objetivos, conjuntos, evoluciones y publicaciones de reglas exigen `validation_status` documentado y `validation_evidence` con edición, URL pública, observación y vencimiento. El SQL aplica esa condición a relaciones, alias y totales, y oculta definiciones caducadas. Crear o importar manualmente conserva un borrador; `rules_reviewed=true` no acredita la fuente. Cambiar reglas o segmentos invalida la evidencia. Copiar una publicación acreditada conserva su evidencia y mantiene el progreso privado.

`GET /catalog/pending` comunica cantidades pendientes sin publicar reglas/nombres como contenido activo. Las pantallas explican esa separación. Actualmente no hay publicaciones acreditadas de retos/conjuntos/Evos cargadas ni proveedor autorizado que pueda hacerlo: sus operaciones quedan pendientes hasta una revisión técnica de la definición exacta y vigente. No se promete activación por pegar una URL.

0014 preserva saldos y plantillas heredados con origen no verificado. El perfil manual nuevo empieza en cero; recuperar un saldo antiguo requiere una conciliación explícita. Las protecciones de plantillas FC27 históricas siguen excluyendo sus cartas aunque la plantilla esté oculta. Entregas, auditoría y propuestas antiguas solo se muestran cuando acreditan el nuevo alcance; sus registros y reservas permanecen almacenados.

## Contenido, IA y compatibilidad (sprint 9)

Las once formaciones conservan fuente y vigencia documental hasta el 10-nov-2026. El 4-3-3 tiene tres MC; el 4-3-3 Holding tiene MCD y dos MC. Las posiciones proceden de las páginas FC27 de FUT.GG, NealGuides y la referencia R19. No se publican códigos sin comprobar ni se presentan las tácticas propias como meta oficial. Al vencer la revisión se bloquean nuevas propuestas y se ocultan las plantillas afectadas, conservando sus protecciones.

El contenido incorporado contiene dos artículos oficiales fechados: [Ultimate Team Deep Dive](https://www.ea.com/games/ea-sports-fc/fc-27/news/pitch-notes-fc27-fut-deep-dive) y [actualización de lanzamiento](https://www.ea.com/games/ea-sports-fc/fc-27/news/fc-27-fut-developer-launch-update). Las noticias requieren edición, publicación, observación y vigencia. La consulta automática descubre enlaces públicos; los que carecen de revisión quedan pendientes, sin convertir la fecha de descarga en fecha de publicación. Se retiró la tabla de puntos no acreditada. Las 50 referencias conservan su alcance: 29 consultas documentales vigentes y 21 pendientes, incluidas tres fichas inaccesibles y los vídeos sin análisis de su contenido. La etiqueta `Rare` de FUT.GG es vocabulario del proveedor, no acreditación de la clasificación oficial EA.

Ollama solo elige entre enfoques permitidos. La API redacta el resumen desde cantidades filtradas de FC27; nunca muestra prosa libre del modelo. La pregunta se reduce a una intención antes de enviarla o conservarla. El historial anterior queda oculto sin borrarse. Las consultas explícitas de otras ediciones se rechazan. La ausencia del modelo conserva el resumen y el resto de módulos. Esto limita el chat a orientación sobre inventario, protecciones y DCP; las propuestas calculadas siguen en sus pantallas específicas.

Companion declara `compatibility_status=pending_verification`, `app_build=null` y `visual_actions_allowed=false`. Incluso una lectura que coincide con una variante documentada permanece en cuarentena hasta comprobar la versión real; posteriormente puede conciliarse por la revisión manual del catálogo, sin afirmar conexión oficial. Las pruebas de puente simulan compatibilidad únicamente en la base desechable. No hay dispositivo real ni adaptador EA aprobado en esta entrega. Las prácticas dejan de publicar instrucciones al vencer su revisión el 25-oct-2026.
