# Reconocimiento guiado de vistas FC27

La extensión 0.3.0 conserva el inspector de regiones y añade edición/importación de definiciones, pruebas y ciclo de vida de perfiles para **vista previa manual**. **No incluye un extractor EA contrastado ni ingesta de páginas reales.** Los mapas no admiten cartas ni verifican identidad. No hay navegación automática en EA.

## Instalación comprobada el 21 de octubre de 2026 (America/Bogota)

`/build.json` y `/api/build` de `http://localhost:8090` coinciden en `ad73edf14bcafa827648f4dc70a4ea7f20e52ad6`, compilación local limpia del 18-oct-2026. Health responde saludable, Alembic current informa `0018` y OpenAPI sí contiene `/reader`. Sus capacidades siguen admitiendo únicamente `semantic-sample-1`, `synthetic_dom` y `user_export_dom`, con extracción de página real y navegación deshabilitadas. Los cinco servicios personales están saludables.

El diagnóstico `4f8eded/0017`, sin `/reader`, fue anterior a la actualización autorizada del 18-oct-2026 y es **histórico**. La PR #7 sigue abierta y en borrador; el despliegue local no es un merge. Esta revisión no actualiza imágenes ni migra la base personal. La versión que esté cargada en el navegador del propietario no se ha inspeccionado: el panel 0.3.0 muestra su versión efectiva junto al ID, para distinguirla de ZIP antiguos.

El origen canónico es `http://localhost:8090`. Una preferencia existente de la extensión se conserva, incluso al desconectar. Cambiarla durante el emparejamiento exige marcar confirmación; comprobar otro destino no lo guarda ni busca puertos. `127.0.0.1` utiliza otras cookies. El lector compara `/build.json`, `/api/build`, OpenAPI y `/reader/capabilities` antes de emparejar o activar; el inspector funciona sin backend. Las capacidades públicas no devuelven datos de cuenta ni conceden acceso.

## Obtener la evidencia mínima en el navegador personal

1. Carga la carpeta compilada `extension/.output/chrome-mv3` desde **chrome://extensions → Modo desarrollador → Cargar descomprimida**. Alternativamente descomprime el ZIP privado entregado en `state/` y carga esa carpeta. No es una publicación en la tienda.
2. Abre la Web App oficial. Introduce contraseña y MFA exclusivamente en EA. El botón de la extensión reutiliza su pestaña; puedes seleccionar una ya abierta pulsando el icono de la extensión en ella.
3. Ya dentro del club, selecciona texto de una región: cabecera, lista, ficha, principal o un requisito de DCP/objetivo. Abre el panel con el icono, declara la vista y pulsa **Reconocer estructura de esta región**. La vista es una declaración, no una clasificación verificada.
4. Repite mientras navegas personalmente. El panel conserva hasta ocho mapas privados, fuera de la página de EA. No envía mapas al backend. El inspector no necesita emparejamiento.
5. Abre la vista previa. Revisa textos y etiquetas, elimina los mapas si no deseas conservarlos y, cuando estén revisados, marca la casilla y exporta. Comparte únicamente el JSON revisado o su ruta local, nunca cookies, HAR, perfil de Chrome ni HTML completo.

## Qué recoge y qué queda pendiente

Una región seleccionada, como máximo dos contenedores ascendentes, 400 nodos visitados, 120 visibles, profundidad siete y 64 KB de resultado. No recorre `body`; omite formularios, entradas, contenido editable, scripts, iframes y nodos ocultos. Recoge etiquetas, roles permitidos, clases CSS acotadas, texto corto visible, `aria-label`, `aria-busy` y `aria-rowcount`. No recoge atributos arbitrarios, valores de entrada, URLs de imágenes/enlaces, contenido de canvas (tampoco su texto alternativo), almacenamiento ni HTML. No cruza shadow DOM. Los límites y el truncamiento se muestran explícitamente.

`coverage.omitted` cuenta campos sensibles, textos mayores de 100 caracteres, subárboles excluidos/ocultos, imágenes, canvas, shadow/custom elements y nodos de texto mixto. Los contadores se refieren a lo encontrado dentro del recorrido acotado, no al contenido interior omitido. `coverage.partial` señala las omisiones sin certificar cobertura. Un requisito largo queda desconocido, nunca recortado para aparentar validez. Una carta sin texto seleccionable sigue requiriendo seleccionar un encabezado cercano; no se añadieron capturas globales ni eventos de clic sobre EA. Selección explícita de regiones sin texto: pendiente de evaluar con los mapas reales.

El filtro de privacidad permite vocabulario como «Token planner» y «Gallery Tokens», conservando el bloqueo de formularios de acceso, contraseñas, MFA, etiquetas de credencial (`access_token`, `refresh token`, `token=`, token de acceso) y valores con aspecto de secreto. No certifica que cualquier texto restante sea publicable: la exportación sigue requiriendo revisión.

Los controles son candidatos con `approved=false`. Su nombre no acredita un efecto seguro. `virtualized`, filtros y página permanecen desconocidos si no hay un perfil que los interprete. Fin de lista y cobertura global no se afirman. Un detector de secretos reduce riesgos, pero no reemplaza la revisión humana de la exportación.

Cada mapa conserva fecha local, referencia de documento y procedencia: `local_region_map` para regiones del formato local (sin presumir si sus datos son sintéticos o exportados) y `observed_page_map` para la ruta oficial. La ingesta existente conserva por separado `synthetic_dom` y `user_export_dom`. La fecha es de lectura del DOM, no de actualización remota de EA. La firma usa estructura, roles y selectores, sin textos personales, saldo ni nombre del club. El perfil queda `proposed`, sin extractores ni transiciones habilitadas. No se ejecuta configuración recibida ni código remoto.

## Definición y prueba de perfiles

El `ViewProfile` del mapa sigue siendo una propuesta inerte. Desde el panel se crea una definición `club-lab-extractor-1` vinculada a ese mapa. Sus localizadores deben existir en él y solo permiten etiqueta y clases; no se ejecutan CSS arbitrario, JavaScript, atributos de entrada ni instrucciones de navegación. El ámbito raíz es la región revisada; cada campo debe ser único **dentro de su registro**, aunque su selector se repita en otras cartas. Archivo importado y editor JSON pasan por el mismo validador; la importación no admite estados ni evidencia.

El ciclo implementado es `draft → sample_tested → observed_contrasted → active`, con desactivación explícita. Se guardan como máximo ocho perfiles privados en la extensión. Cada cambio de definición incrementa la revisión y elimina sus pruebas; la evidencia también se vincula a la revisión del lector `bounded-region-1`. La muestra propia debe reproducir la estructura y el idioma de la definición; pasar una prueba local nunca acredita EA. Para registrar contraste se exige prueba previa, una vista previa real del mismo documento y revisión de sus campos. Se vuelve a leer la región al confirmar; cambios de contenido, documento o revisión, y una espera superior a cinco minutos, invalidan esa confirmación. El origen y la ruta, incluido su fragmento, deben coincidir con el mapa real. Los fragmentos con parámetros, codificaciones o indicios de credenciales se rechazan antes de guardar un mapa. No se incorpora ningún selector EA supuesto.

Prueba, contraste y lectura manual activa usan `extractProfile` sobre un mapa **nuevo** del mismo inspector acotado. Carga, truncamiento, idioma desconocido/diferente, estructura distinta, registros solapados, campos obligatorios desconocidos o selectores ambiguos impiden producir la vista previa. Un fallo de un perfil contrastado revoca su contraste y lo desactiva. La firma estricta incluye cantidad/estructura de filas; puede exigir nueva revisión ante variaciones legítimas. No se presenta como compatibilidad flexible con listas virtualizadas.

Los resultados separan campos por vista: carta, puesto, cabecera, texto de requisito y progreso. Los opcionales ausentes son `null`; enteros solo admiten dígitos sin asumir separadores/unidades, booleanos admiten valores explícitos y las posiciones requieren abreviaturas españolas reconocidas. Saldo, puntuación y progreso son campos distintos; no se derivan precios ni presupuesto. Requisitos de DCP/objetivos permanecen texto, **sin inferir operadores mínimos/máximos/igualdad** ni reglas utilizables por el solver. Estas vistas previas no son los payloads de ingesta tipados solicitados para P0-D.

**Activo significa aquí lector de vista previa manual**, siempre con `ingestion_enabled=false`, `provider_verified=false`, sin solicitudes al backend, observador, temporizador o navegación. No se usa la prueba para ampliar `admitted()` ni para saltarse la revisión de lotes existente.

## Dependencias que siguen abiertas

P0-A: falta exportación privada revisada de cabecera/cuenta, lista, detalle, principal y un DCP u objetivo, y comprobar la extensión realmente cargada. P0-B dispone del ciclo y lector de prueba, pero ningún perfil ha sido contrastado con una sesión EA personal. P0-C/P0-D: siguen pendientes el origen real end-to-end, su revisión de extractor persistida y payloads de ingesta por dominio basados en esa evidencia; no se ha añadido `observed_page_dom` ni modificado admisión. No se ha cerrado el caso real mapa → ingesta → propuesta con principal protegida.

Después siguen fragmentación mayor de 30 filas, recibos/finalización de observaciones, actualización no conflictiva y recorridos con checkpoints/reanudación. La prueba personal de solo lectura permanece pendiente; una prueba sintética no sustituye esa evidencia. El lector de muestras anterior conserva sus contratos y límites. La siguiente entrada necesaria es la ruta del JSON revisado exportado por el inspector existente, sin cookies, HAR, credenciales o perfil del navegador.

## Condiciones y operación

Se consultaron las [reglas de EA](https://help.ea.com/en/articles/ea-sports-fc/fc-rules/) el 18 de octubre de 2026: advierten sobre extensiones y prohíben bots/automatización. El permiso temporal `activeTab` no es una autorización del proveedor. El inspector se limita a observación guiada; no realiza transacciones ni descubre acciones mediante pulsaciones.

El navegador personal nunca se copia a Playwright. Las pruebas usan Chromium y perfiles desechables, mapas sintéticos, PostgreSQL temporal y limpieza por identidad. Una prueba sintética acredita controles del mecanismo, no compatibilidad con EA. No se cambia la principal ni las reglas de admisión/consumo. Un despliegue personal requiere decisión específica, respaldo restaurado aparte y recuperación preparada según [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md).
