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
