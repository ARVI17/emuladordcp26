# Actualización automática del club · decisión de producto

Revisión: **17-nov-2026**. Estado: **requisito pendiente; no hay sincronización automática EA en Club Lab**. Este documento sustituye el recorrido manual como objetivo de producto, sin atribuir al código funciones que todavía no existen.

## Resultado que pide el propietario

Abrir Club Lab y encontrar actualizado el club de **FC27 en PS5**, con su once y siete suplentes protegidos. La aplicación debe consultar los datos, conciliar cambios y calcular recomendaciones sin pedir capturas, texto copiado, navegación página por página ni revisión de cada carta. El acceso inicial/MFA de EA y la resolución de una discrepancia excepcional pueden necesitar al propietario. Una sesión caducada debe indicarlo y conservar la última lectura con su fecha real.

La pantalla principal debe responder automáticamente:

1. **Mi equipo:** principal observada y protegida, tres alternativas y mejora concreta por puesto.
2. **DCP que puedo hacer:** posibles con el club, posibles comprando lo que falta y descartados, con recompensa, vencimiento, sacrificio y efecto sobre la plantilla. Preparar la composición no equivale a entregar el DCP en EA.
3. **Cartas que puedo vender:** solo copias transferibles y prescindibles, con ofertas observadas del mercado correspondiente a PS5, intervalo de precio, antigüedad e ingreso neto estimado. No recomendar una venta solo porque la carta no esté en el once.
4. **Qué comprar:** mejoras compatibles con presupuesto actual, reserva y química/posiciones conocidas. Una venta propuesta no aumenta el saldo.

Las propuestas se recalculan al publicar datos nuevos, no en cada render. Fecha de apertura, fecha de consulta y fecha de origen son distintas. Nunca mostrar «actualizado» por recalcular las veinte cartas antiguas.

## Comprobación de las opciones de conexión

| Opción | Evidencia comprobada | Consecuencia para Club Lab |
| --- | --- | --- |
| Community API de EA | [Anuncio oficial, 27-jul-2026](https://www.ea.com/games/ea-sports-fc/news/pitch-notes-fc26-community-api-update) y [ayuda oficial](https://help.ea.com/en/articles/ea-sports-fc/community-api/): socios aprobados FUT.GG, FUTBIN y FUTWIZ; EA indica que no acepta nuevas solicitudes actualmente. | No se dispone de alta pública, credenciales ni contrato de integración para Club Lab. No inventar OAuth ni reutilizar permisos de un socio. |
| FUT.GG | [GG Club vigente](https://www.fut.gg/gg-club/) anuncia sincronización de jugadores, plantillas, Evos, tácticas y estadísticas mediante la conexión oficial. | Es una alternativa para usar el servicio externo. La página consultada no acredita exportación/API para Club Lab, coste de todas las funciones ni frecuencia exacta. No presentar su autorización como nuestra. |
| FUTWIZ | [Squad Sync](https://www.futwiz.com/futwiz-sync) documenta importación gratuita de plantillas y actualización mediante re-sync. | Gratuidad comprobada para esas funciones; no demuestra inventario completo, entrega de DCP, ventas automáticas ni actualización de Club Lab en cada apertura. |
| Conector instalado | Búsqueda de plugins EA SPORTS FC/FUTBIN/FUTWIZ sin coincidencias en el directorio consultado. | No se encontró un conector utilizable en esta sesión; no afirma que todos los directorios posibles carezcan de él. |
| WXT en Chrome | [WXT](https://wxt.dev/) es una herramienta MIT para extensiones. El repositorio ya la usa; el manifiesto actual solo concede hosts locales y el lector automático admite muestras/exportaciones propias. | Candidato para el puente local solicitado. Aún faltan extractor EA, navegación, identidad de copias, permisos de sitio y disparador al abrir Club Lab. No constituye una conexión oficial. |
| Playwright / Selenium | Automatizan interfaces de navegador; [Playwright](https://playwright.dev/docs/intro) ya se emplea en las pruebas del proyecto. | Playwright sirve para verificar el recorrido. Añadir además Selenium duplicaría infraestructura sin resolver acceso, identidad ni cobertura. |
| Requests + BeautifulSoup / Scrapy | Clientes HTTP y extracción; la [documentación de Scrapy](https://docs.scrapy.org/en/latest/topics/dynamic-content.html) distingue contenido generado dinámicamente y navegación. | No aportan por sí solos sesión autorizada, navegación JavaScript ni un protocolo EA. No añadir las cuatro tecnologías para resolver el mismo acceso. |

La guía antigua de GG Club de octubre de 2025 describe una sincronización por nombre de plantilla y un límite diario. No se toma como contrato del servicio actual: la portada vigente ya describe la conexión oficial EA. Los límites del producto conectado requieren comprobación adicional.

## Hechos observados en Chrome

En la sesión personal se pudieron leer veinte filas visibles de `My Club Players`, abrir `Player Bio` y volver a la lista. La ficha ofrece campos adicionales de variante, liga, club y nacionalidad. Se vieron los controles Previous/Next y Compare Price; **no se ejecutó paginación ni consulta del mercado en esta comprobación**.

Las veinte filas inspeccionadas solo tenían clases CSS; no se encontraron atributos `id`, `data-id`, `data-item-id`, `data-resource-id` o `data-instance-id` en ellas o sus descendientes. Tampoco aparecieron esos atributos en la ficha examinada. Hay filas con el mismo nombre, media y posición. Esto no prueba que no exista otro dato de identidad accesible; sí impide acreditar una clave estable con esta muestra. No guardar nombres ni inventario en este documento.

No se consultaron cookies, tokens, objetos internos de EA ni endpoints privados. No se creó una nueva carga local durante esta revisión.

## Decisión de implementación

Conservar **WXT como candidato al puente de lectura local**, React/FastAPI/PostgreSQL/OR-Tools como aplicación y Playwright como verificador. No desarrollar más formularios de importación como siguiente incremento. Primero resolver el acceso y la identidad que hacen posible la automatización. Si una exportación/integración documentada de un socio oficial permite alimentar Club Lab, evaluarla antes de mantener otro extractor. Su disponibilidad sigue sin comprobarse.

El primer prototipo debe producir una evidencia acotada de viabilidad, sin promoverla a inventario verificado:

1. Desde una única configuración autorizada, detectar la apertura de Club Lab y la sesión del sitio permitido. No pedir selección de pestaña en cada uso. Identificar plataforma, edición y contexto antes de publicar; cambio de club o sesión detiene la publicación.
2. Leer listas y detalles mediante controles visibles contrastados EN/ES. Distinguir atleta, variante y copia; una imagen o resource ID de variante no identifica la copia poseída. Si falta clave estable, contrastar una reconciliación conservadora y dejar las discrepancias fuera de consumo/venta. No usar posición en la lista como identidad.
3. Recorrer páginas con límites, cancelación, detección de carga/repetición y recuperación desde checkpoint. Un filtro, una página o una lista virtualizada no acreditan todo el club. La ausencia parcial no retira cartas ni revive consumidas.

Solo después de ese contraste se implementará el transporte automático: canal restringido al origen local autorizado, credencial privada de la extensión, lotes con ID/hash/secuencia/contexto/fecha, publicación atómica e idempotente y estado visible. Revocar el permiso debe detener lecturas y publicación. No habilitar una ruta pública que acepte snapshots como prueba de propiedad.

Después: principal y banquillo por puestos reales, lectura de DCP vigentes, consulta limitada de ofertas en el mercado del juego y análisis automático. Cada dominio conserva cobertura y fecha independientes; el acceso al inventario no acredita acceso a precios o reglas. No quitar `require_module` ni promover textos revisados a proveedor autenticado para hacer funcionar la pantalla.

## Prueba de aceptación que falta

- **Dos aperturas reales** de Club Lab actualizan las veinte copias sin pegar texto, compartir pantalla ni revisar una por una; mismos IDs, cambios observados reflejados y copias legítimas separadas.
- Probar una ambigüedad, reordenación, páginas solapadas, sesión caducada, cambio de contexto, cancelación y reinicio. Un fallo conserva el último estado y muestra su antigüedad.
- Once y siete suplentes identificados por puestos y protegidos en ambos ciclos; ninguna suposición basada en las primeras dieciocho filas.
- Un DCP real produce una composición válida; otro caso explica faltantes. Una propuesta de venta usa transferibilidad observada y ofertas actuales del mercado correspondiente a PS5. Ambos excluyen protegidas.
- Análisis repetido sin compra, venta ni consumo. Entrega final de DCP y publicación de ventas no forman parte del lector; siguen requiriendo una acción deliberada del propietario conforme al alcance vigente.

La carga anterior de veinte cartas y sus dos relecturas **no pasan estos criterios**: requirieron revisión asistida. Son evidencia técnica parcial preservada, no aceptación del producto automático. No se puede prometer operación con Chrome cerrado o sin sesión EA usando solamente un puente de navegador.
