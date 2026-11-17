# Primera carga del club real

Objetivo de la siguiente sesión: revisar **20 cartas reales**, corregir dos lecturas, repetir una vista sin duplicar y proteger el once más siete suplentes. Todavía no se ha aceptado este recorrido con el club personal. Las pruebas automáticas usan datos sintéticos.

## Acceso mediante Chrome y WXT

1. Verificar la conexión oficial de Chrome con el chat antes de operar su sesión. En Ajustes → Uso del ordenador, Google Chrome debe estar conectado; el corte del 16-nov mostró **Extensión del navegador no instalada**. [Instalación y recuperación oficiales](https://learn.chatgpt.com/docs/chrome-extension). No confundir esa extensión de ChatGPT con el lector WXT de Club Lab. Si falla la verificación de URL, corregir la conexión admitida; no sustituirla por extracción de cookies, CDP directo o un perfil copiado.
2. Compilar/cargar WXT 0.5.1 desde una carpeta local identificada y comprobar su versión. En Mi cuenta seleccionar el contexto asistido existente; emparejar el ID de esa extensión con el backend del mismo origen. `localhost` y `127.0.0.1` mantienen sesiones distintas. No recrear un contexto por una lectura vacía.
3. En la pestaña EA oficial ya abierta, conceder el permiso temporal con el icono WXT. Reconocer una región pequeña, asignar los campos observados, probar la definición, comparar una vista previa nueva y activar esa revisión. El programa no distribuye selectores EA contrastados: si la región no permite una lectura inequívoca, detenerse y registrar el impedimento.
4. Enviar las veinte cartas visibles como observación parcial y revisarlas en Club Lab. Conservar desconocidos y no admitir campos incorrectos para alcanzar la cuota. Verificar IDs locales por copia antes y después de **dos nuevas lecturas**. Repetir el mismo recibo también debe ser idempotente, pero no sustituye las lecturas nuevas. Resolver cambios de campos/copia explícitamente; no mezclar dos copias legítimas por nombre.
5. Leer la principal real por separado, con once puestos y siete suplentes observados. Registrar y proteger explícitamente esas dieciocho copias; la lista de inventario no acredita qué equipo está activo. Una protección local no cambia EA.

La prueba `extension/tests/first20.spec.ts` reproduce el transporte, las dos relecturas y las dieciocho protecciones con datos **sintéticos**. No acredita pasos completados en la cuenta del propietario ni automatización de navegación/clics EA. [Resultados](TESTING.md).

## Alternativa de captura visual revisada

1. Comprobar `scripts/fc27.ps1 Estado` y abrir [Club Lab local](http://localhost:8090). Contrastar versión servida y estado en [NEXT_SESSION](NEXT_SESSION.md). La edición debe ser FC27; elegir expresamente el contexto de lectura asistida/visual de la cuenta. El contexto local histórico no se convierte automáticamente en tu cuenta.
2. El propietario inicia sesión en la Web App oficial por su cuenta. En Club Lab abre **Escanear mi club**, revisa sección y máscaras de privacidad, marca el consentimiento y pulsa **Compartir pestaña y comenzar escaneo**. Elige únicamente la pestaña de juego ya abierta. No compartir la pantalla de acceso, correo o pagos.
3. Mostrar un grupo pequeño de cartas y esperar a que quede estable. Pausar y usar **Revisar lote detectado** antes de recorrer todo el club. El OCR de filas legibles está probado con ejemplos sintéticos; la segmentación de fichas gráficas reales aún necesita contraste. Cero candidatas o identidad ambigua no equivale a club vacío: detener y revisar una muestra permitida antes de continuar.
4. Contrastar nombre, media, posición, variante y cada copia. Corregir dos lecturas y dejar desconocido todo campo que no se vea. No deducir transferibilidad, cesión, Evo u holografía del nombre o de una ficha pública. R33/Nuno Mendes y R49/Sophia Wilson siguen pendientes de distinguir sus presentaciones del catálogo; no elegirlas por parecido.
5. Seleccionar solamente copias revisadas, confirmar edición/propiedad/agrupación y escribir **GUARDAR SINCRONIZACION**. El resultado debe indicar snapshot, nuevas/actualizadas/conservadas y cobertura parcial. Las cartas que no aparezcan se conservan; el guardado es local.
6. Repetir una vista del mismo contexto. Vincular la copia existente cuando corresponda y comprobar que no se crean duplicados. Una segunda copia legítima sigue siendo independiente. Completar hasta 20 cartas revisadas; no marcar el inventario como completo por alcanzar ese número.
7. En Plantillas seleccionar explícitamente la principal y proteger once, banquillo y reservas pertinentes. Comparar después al menos tres alternativas con formaciones vigentes y datos disponibles. Las carencias de posiciones/atributos se muestran; media y química son aproximaciones locales.

Registrar localmente en `state/` únicamente IDs de lote/snapshot, cantidades, correcciones, coincidencias y errores públicos; no imágenes, credenciales ni inventario en Git. Actualizar `PROJECT_STATE.json` (DATA-1, DATA-2 y TEAM-1) solo con resultados observados y regenerar `PROJECT_STATUS.md`.

Si el OCR falla, conservar el lote pendiente y describir el patrón de error para el siguiente incremento del extractor. La lectura manual revisada de una ficha es la alternativa existente. Nunca crear cartas desde el catálogo para simular una importación correcta.

Después de aceptar el club y proteger la principal: revisar un DCP real con fuente/requisitos/expiración; evaluar prescindibles transferibles y cotizaciones verificadas. Las simulaciones de mercado en modo visual siguen limitadas por cobertura. Faltan precios, reglas reales de Galería y contraste de copias antes de prometer recomendaciones completas. Club Lab no conecta la cuenta por introducir un usuario ni ejecuta compras, ventas o entregas EA.
