# Revisión documental · 16 de noviembre de 2026

Consulta pública realizada en esta sesión; corte registrado **2026-11-16 22:10:56 UTC**. Ventana local de revisión de 30 días, hasta **2026-12-16 22:10:56 UTC**, exclusiva. Esa fecha exige volver a contrastar: no es una fecha de expiración publicada por EA ni acredita desafíos activos. No hay renovación automática.

## Formaciones

Se contrastaron posiciones en las páginas indicadas. Se mantienen 11 identificadores y diez composiciones distintas: `4-1-2-1-2` conserva su significado histórico como alias de la estrecha. No se cambian plantillas guardadas.

| Identificadores | Fuente contrastada |
| --- | --- |
| 4-2-1-3, 4-2-3-1 abierta, 4-4-1-1 mediocampo, 4-4-2, 4-1-2-1-2 estrecha y alias | [NealGuides: formaciones FC27](https://nealguides.com/best-fc-27-formations/) |
| 4-3-3 (tres MC) | [FUT.GG 4-3-3](https://www.fut.gg/tactics/4-3-3/) |
| 4-3-3 Holding (MCD y dos MC) | [FUT.GG Holding](https://www.fut.gg/tactics/4-3-3-holding/) |
| 4-2-3-1 (tres MCO) | [FUT.GG 4-2-3-1](https://www.fut.gg/tactics/4-2-3-1/) |
| 4-3-1-2 | [FUT.GG 4-3-1-2](https://www.fut.gg/tactics/4-3-1-2/) |
| 3-5-2 | [FUT.GG 3-5-2](https://www.fut.gg/tactics/3-5-2/) |

`fc27_formations.json` registra las once posiciones, fuente e intervalo por identificador. El servidor excluye revisiones futuras, vencidas, revocadas, sin zona horaria o con posiciones incompatibles con la definición cargada. Los códigos tácticos siguen sin acreditar y el encaje sigue siendo una hipótesis local, sin garantía deportiva.

## Contenido y referencias

- R01 y las cinco descripciones generales: [EA FUT Deep Dive](https://www.ea.com/games/ea-sports-fc/fc-27/news/pitch-notes-fc27-fut-deep-dive). Revisados Galería, base de Evos, exclusión de cesiones, presentaciones holográficas, cambios de rareza, contribuciones parciales y caminos de evolución. No se incorpora una tabla numérica de puntos.
- Segundo artículo: [EA actualización de lanzamiento](https://www.ea.com/games/ea-sports-fc/fc-27/news/fc-27-fut-developer-launch-update), fecha editorial 1-oct-2026. Es noticia histórica, no inventario de DCP activos.
- R05: [EA Community API](https://help.ea.com/en/articles/ea-sports-fc/community-api/). Socios publicados: FUTBIN, FUT.GG y FUTWIZ. No concede acceso a Club Lab; `ADAPTERS` permanece vacío.
- R09: [EA Gameplay Deep Dive](https://www.ea.com/games/ea-sports-fc/fc-27/news/pitch-notes-fc27-gameplay-deep-dive). Revisados defensa manual y controles de desmarque curvo/pase con continuación; parche y configuración personal desconocidos.
- R14/R16: [formaciones](https://nealguides.com/best-fc-27-formations/) y [defensa](https://nealguides.com/fc-27-defending-tips/) del autor. Solo sus explicaciones textuales: no precios, promesas de resultados ni vídeos no observados.
- R19: [texto de Yuyu sobre 4-3-1-2](https://note.com/yuyugamesyoutube/n/nf627565b75df); R24: [índice de formaciones FUT.GG](https://www.fut.gg/tactics/). El contraste de posiciones de 4-3-1-2 usa ahora su ficha específica de FUT.GG.

Resultado: **27 referencias documentadas y 23 pendientes**. Se conserva el registro de la revisión anterior. Las prácticas dependen de la vigencia de R09/R16, sustituyendo la fecha fija del 25-octubre.

## Identidad de cartas y actualización

Se abrieron las 22 fichas antes documentadas y se contrastaron edición, identificador, nombre, media, posición y etiqueta del catálogo. Veinte mantienen correspondencia; dos presentan ambigüedad entre Standard y Pristine Holographic. `Rare` se conserva como etiqueta del proveedor, sin convertirla en rareza oficial ni inferir el campo `rare` de una copia.

R33 (Nuno Mendes, 67361009) y R49 (Sophia Wilson, 67372876) pasan a pendientes: el encabezado muestra Pristine Holographic y existe selector de presentación. Falta contrastar identificadores de ambas presentaciones; compartir nombre/media/posición no prueba equivalencia. R26/R31/R35 siguen pendientes; no se inventa una ficha accesible.

La migración **0022** lleva un manifiesto congelado, independiente de futuros archivos de aplicación. Solo actualiza filas que coinciden exactamente con identidad, URL, estado, fechas y evidencia del paquete antiguo. Conserva revocaciones, revisiones posteriores y cambios manuales. Guarda el recibo previo y es idempotente. No modifica jugadores, posesión, Galería, precios, reservas o consumos. La restauración requiere respaldo probado. El arranque normal continúa sin sobrescribir registros existentes.

Las pruebas de flujo usan copias temporales con ventanas explícitas de prueba, sin cambiar el reloj real ni los validadores. `test_public_review.py` usa los archivos versionados y prueba instantes anteriores, iniciales y finales, caducidad individual, alias y conservación de revisiones en la migración. Un pase de tests no sustituye esta consulta documental.

## Fichas contrastadas

Nombre y etiqueta pertenecen a FUT.GG. La existencia de una ficha pública no acredita que el propietario tenga esa carta.

| Ref. | Variante | Carta | Media | Posición | Resultado |
| --- | --- | --- | ---: | --- | --- |
| R27 | 245956 | [Christiane Endler](https://www.fut.gg/players/245956-christiane-endler/27-245956/) | 85 | POR | Documentada |
| R28 | 203376 | [Virgil van Dijk](https://www.fut.gg/players/203376-virgil-van-dijk/27-203376/) | 88 | DFC | Documentada |
| R29 | 236479 | [Mapi León](https://www.fut.gg/players/236479-mapi-leon/27-236479/) | 88 | DFC | Documentada |
| R30 | 243715 | [William Saliba](https://www.fut.gg/players/243715-william-saliba/27-243715/) | 88 | DFC | Documentada |
| R32 | 67336110 | [Lucy Bronze](https://www.fut.gg/players/227246-lucy-bronze/27-67336110/) | 86 | DFC | Documentada |
| R33 | 67361009 | [Nuno Mendes](https://www.fut.gg/players/252145-nuno-mendes/27-67361009/) | 89 | LI | Pendiente: presentación |
| R34 | 265674 | [Selma Bacha](https://www.fut.gg/players/265674-selma-bacha/27-265674/) | 86 | LI | Documentada |
| R36 | 237289 | [Patri Guijarro](https://www.fut.gg/players/237289-patri-guijarro/27-237289/) | 88 | MCD | Documentada |
| R37 | 239053 | [Federico Valverde](https://www.fut.gg/players/239053-federico-valverde/27-239053/) | 87 | MC | Documentada |
| R38 | 251854 | [Pedri](https://www.fut.gg/players/251854-pedri/27-251854/) | 90 | MC | Documentada |
| R39 | 241667 | [Aitana Bonmatí](https://www.fut.gg/players/241667-aitana-bonmati/27-241667/) | 90 | MC | Documentada |
| R40 | 252371 | [Jude Bellingham](https://www.fut.gg/players/252371-jude-bellingham/27-252371/) | 90 | MCO | Documentada |
| R41 | 256630 | [Florian Wirtz](https://www.fut.gg/players/256630-florian-wirtz/27-256630/) | 86 | MCO | Documentada |
| R42 | 246669 | [Bukayo Saka](https://www.fut.gg/players/246669-bukayo-saka/27-246669/) | 87 | ED | Documentada |
| R43 | 227102 | [Caroline Graham Hansen](https://www.fut.gg/players/227102-caroline-graham-hansen/27-227102/) | 89 | ED | Documentada |
| R44 | 238794 | [Vini Jr.](https://www.fut.gg/players/238794-vinicius-jr/27-238794/) | 89 | EI | Documentada |
| R45 | 269404 | [Salma Paralluelo](https://www.fut.gg/players/269404-salma-paralluelo/27-269404/) | 87 | EI | Documentada |
| R46 | 239085 | [Erling Haaland](https://www.fut.gg/players/239085-erling-haaland/27-239085/) | 91 | DC | Documentada |
| R47 | 228093 | [Marcus Thuram](https://www.fut.gg/players/228093-marcus-thuram/27-228093/) | 85 | DC | Documentada |
| R48 | 231747 | [Kylian Mbappé](https://www.fut.gg/players/231747-kylian-mbappe/27-231747/) | 91 | DC | Documentada |
| R49 | 67372876 | [Sophia Wilson](https://www.fut.gg/players/264012-sophia-wilson/27-67372876/) | 89 | DC | Pendiente: presentación |
| R50 | 258980 | [Alessia Russo](https://www.fut.gg/players/258980-alessia-russo/27-258980/) | 88 | DC | Documentada |
