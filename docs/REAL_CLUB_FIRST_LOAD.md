# Primera carga del club real

**Incremento vigente, 17-nov:** app **988bbbd/0023 desplegada** y WXT **0.6.0** probado dos veces con veinte copias EN/ES, reaperturas sin duplicados y dieciocho candados sintéticos. Instalación personal de esa extensión y aceptación automática todavía pendientes; la UI no la detectó. La principal real ya se observó por puestos, pero no se guardó/protegió en esta sesión. Continuar desde [NEXT_SESSION](NEXT_SESSION.md), con el artefacto `state/wxt-auto-release-20261117/chrome-mv3`; no usar las instrucciones antiguas de 0.5.1 como siguiente paso.

**Prioridad posterior del propietario (17-nov):** este recorrido asistido no satisface el producto solicitado. Debe sustituirse como camino habitual por actualización y análisis automáticos al abrir la app. [AUTO-1: conexión, límites y prueba exigida](AUTOMATIC_CLUB_SYNC.md). Las instrucciones siguientes describen la alternativa manual existente, no la siguiente fase de desarrollo.

**Antecedente del 17-nov-2026: primera carga asistida realizada.** Veinte cartas reales revisadas desde Chrome y dos lecturas nuevas con los mismos IDs, sin duplicados. Seis atributos por carta; posiciones EN/ES normalizadas. La UI muestra las 20 copias. En ese corte anterior todavía no se habían observado el once y los siete suplentes; su protección sigue pendiente. [Continuidad y recuperación](NEXT_SESSION.md).

## Vía sencilla disponible

En el contexto asistido existente, abre **Mi cuenta → Leer cartas desde texto visible**. El agente puede leer las filas visibles de Chrome conectado y trasladarlas como `MEDIA POSICIÓN NOMBRE | ATRIBUTOS`; también puedes transcribirlas. **Preparar revisión del texto** solo crea candidatas. Contrasta nombres, medias, posiciones y atributos; deja desconocido lo que no se vea. Confirma edición/propiedad/correspondencia y escribe `GUARDAR OBSERVACION` para guardar.

Repetir la misma página reutiliza el recibo. Para una observación nueva, cambia su etiqueta de página y selecciona explícitamente cada copia local que corresponda. Una coincidencia de nombre no acredita por sí sola identidad. Las filas ambiguas o retiradas se bloquean, sin fusionarlas ni reactivarlas. Esta vía declara `user_reviewed_text`, nunca identidad EA verificada; su cobertura sigue siendo parcial. [Contrato y límites](ASSISTED_READING.md).

**Pendiente tras resolver AUTO-1:** obtener la plantilla activa por puestos y proteger once/siete suplentes mediante la lectura contrastada. El lector de texto actual solo admite inventario; no inferir la principal del orden de las veinte cartas ni ampliar la transcripción de plantilla como solución principal. La carga actual se conserva.

Las rutas y los rechazos OCR descritos a continuación corresponden al **16-nov**, antes de esta carga. No representan el estado de inventario actual.

## Rutas gratuitas contrastadas (16-nov-2026)

El propietario pidió reducir pasos, buscar documentación/proyectos y evitar pagos. Investigación de fuentes primarias; no se instaló software externo ni se conectó su cuenta a estos servicios.

| Opción | Gratuidad y utilidad comprobadas en su documentación | Límite para este proyecto |
| --- | --- | --- |
| [FUTWIZ Squad Sync](https://www.futwiz.com/futwiz-sync) | Importación y consulta gratuitas de plantillas FC27, mediante cuenta gratuita FUTWIZ y conexión oficial EA. Es la opción lista más sencilla para consultar el equipo. | La página documenta plantillas; no demuestra exportación CSV/JSON del club completo ni importación a Club Lab. Conectar una cuenta a FUTWIZ es un paso distinto. |
| [FC-Tracker](https://github.com/fc-tracker/fc-tracker) | Su README declara uso gratuito, sin suscripción, cuenta opcional, lector visual para Galería y extensión opcional de sincronización. | Sincronización no oficial que consulta pantallas/datos de la Web App. Licencia PolyForm Strict: no copiar/modificar/redistribuir como si fuese MIT. No se ha validado compatibilidad de una exportación con Club Lab. |
| [FC27 Copilot](https://github.com/liusihang/fc27-copilot) | Código original MIT; proyecto local para inventario, consultas y planificación DCP mediante MCP. | Requiere servicio Python, extensión descomprimida y cliente MCP. Su [aviso](https://github.com/liusihang/fc27-copilot/blob/main/NOTICE.md) declara endpoints EA no documentados y restricciones de acceso; no simplifica esta instalación ni acredita licencia del catálogo ajeno. |
| [EA FC Automated SBC Solving](https://github.com/Regista6/EA-FC-Automated-SBC-Solving) | Ejemplo de optimización DCP con OR-Tools/CP-SAT. | Requiere obtener el dataset del club con otra extensión. Club Lab ya tiene OR-Tools; añadir este solver no resuelve la lectura. |

[EA confirma FUTBIN, FUT.GG y FUTWIZ como socios aprobados](https://help.ea.com/en/articles/ea-sports-fc/community-api/). Esa aprobación no se transfiere a Club Lab. La alternativa FUTWIZ sirve al objetivo deportivo inmediato, pero no debe anunciarse como sincronización terminada de esta aplicación.

[WXT](https://wxt.dev/guide/introduction) organiza extensiones y [Playwright](https://playwright.dev/docs/intro) permite automatizar/verificar interfaces: ambos ya están en el proyecto. WXT no aporta por sí solo un extractor EA ni evita los permisos de Chrome. No añadir Puppeteer, otro servicio o una extensión de pago para resolver una lectura que ya es accesible mediante el navegador conectado.

Decisión local: reutilizar el lector instalado, acotar la región de cartas, normalizar posiciones EN/ES y llevarla a la revisión existente. Antes de ampliar automatización, contrastar límites de ancestros/profundidad y clases variables del extractor. El resultado deseado es **leer → revisar diferencias → guardar**, sin que el propietario tenga que diseñar selectores. Esto es el siguiente incremento pendiente, no una función ya terminada. CSV/XLSX no reemplazan la evidencia de propiedad: su idempotencia depende del contenido del archivo y no identifica por sí sola la misma copia en dos exportaciones distintas.

## Acceso mediante Chrome y WXT

1. Reutilizar Chrome ya conectado mediante la extensión oficial del chat. [Instalación y recuperación oficiales](https://learn.chatgpt.com/docs/chrome-extension), solo si deja de estar disponible. No confundir esa conexión con el lector WXT de Club Lab. Si falla la verificación de URL, corregir la conexión admitida; no sustituirla por extracción de cookies, CDP directo o un perfil copiado.
2. Contrastar primero la versión del lector WXT instalado. El artefacto 0.5.1 ya está compilado y probado en `state/wxt-first20-release/chrome-mv3`; el agente no puede abrir `chrome://extensions` por la política de navegación, por lo que su carga no se ha realizado. No eludir ese bloqueo. En Mi cuenta conservar el contexto asistido seleccionado; emparejar la extensión con el backend del mismo origen. `localhost` y `127.0.0.1` mantienen sesiones distintas. No recrear un contexto por una lectura vacía; hay varias etiquetas iguales en la UI.
3. En la pestaña EA oficial ya abierta, conceder el permiso temporal con el icono WXT. Reconocer una región pequeña, asignar los campos observados, probar la definición, comparar una vista previa nueva y activar esa revisión. El programa no distribuye selectores EA contrastados: si la región no permite una lectura inequívoca, detenerse y registrar el impedimento.
4. Enviar las veinte cartas visibles como observación parcial y revisarlas en Club Lab. Conservar desconocidos y no admitir campos incorrectos para alcanzar la cuota. Verificar IDs locales por copia antes y después de **dos nuevas lecturas**. Repetir el mismo recibo también debe ser idempotente, pero no sustituye las lecturas nuevas. Resolver cambios de campos/copia explícitamente; no mezclar dos copias legítimas por nombre.
5. Leer la principal real por separado, con once puestos y siete suplentes observados. Registrar y proteger explícitamente esas dieciocho copias; la lista de inventario no acredita qué equipo está activo. Una protección local no cambia EA.

La prueba `extension/tests/first20.spec.ts` reproduce el transporte, las dos relecturas y las dieciocho protecciones con datos **sintéticos**. No acredita pasos completados en la cuenta del propietario ni automatización de navegación/clics EA. [Resultados](TESTING.md).

## Alternativa de captura visual revisada

**Estado real:** se completó el selector nativo y Club Lab mostró captura activa. Dos sesiones independientes de Leer pantalla rechazaron la vista inglesa con el error público de pantalla ajena/sensible/otra edición/ilegible. No hubo candidatas ni admisión y la captura quedó inactiva. El código actual reconoce marcas y posiciones españolas; la causa exacta del rechazo necesita diagnóstico antes de atribuirla solo al idioma. No repetir indefinidamente el selector ni quitar la guarda para aceptar la página. Los pasos siguientes describen el flujo previsto cuando el reconocimiento funcione.

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
