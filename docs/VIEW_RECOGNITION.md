# Reconocimiento guiado de vistas FC27

La extensión 0.2.0 añade un inspector de regiones y un borrador declarativo `ViewProfile`. **No incluye un extractor EA contrastado.** Los mapas no admiten cartas ni verifican identidad. No hay navegación automática en EA.

## Estado comprobado el 18 de octubre de 2026

La instalación personal sirve `http://localhost:8090`, revisión `4f8eded842682a98ba8f9678da5c01feb00547c2`, frontend/API coincidentes y esquema `0017`. No ofrece rutas `/reader`. La rama de trabajo incorpora `0018`; subir código o cargar la extensión no actualiza esa instalación.

El origen canónico es `http://localhost:8090`. Una preferencia existente de la extensión se conserva, incluso al desconectar. Cambiarla durante el emparejamiento exige marcar confirmación; comprobar otro destino no lo guarda ni busca puertos. `127.0.0.1` utiliza otras cookies. El lector compara `/build.json`, `/api/build`, OpenAPI y `/reader/capabilities` antes de emparejar o activar; el inspector funciona sin backend. Las capacidades públicas no devuelven datos de cuenta ni conceden acceso.

## Obtener la evidencia mínima en el navegador personal

1. Carga la carpeta compilada `extension/.output/chrome-mv3` desde **chrome://extensions → Modo desarrollador → Cargar descomprimida**. Alternativamente descomprime el ZIP privado entregado en `state/` y carga esa carpeta. No es una publicación en la tienda.
2. Abre la Web App oficial. Introduce contraseña y MFA exclusivamente en EA. El botón de la extensión reutiliza su pestaña; puedes seleccionar una ya abierta pulsando el icono de la extensión en ella.
3. Ya dentro del club, selecciona texto de una región: cabecera, lista, ficha, principal o un requisito de DCP/objetivo. Abre el panel con el icono, declara la vista y pulsa **Reconocer estructura de esta región**. La vista es una declaración, no una clasificación verificada.
4. Repite mientras navegas personalmente. El panel conserva hasta ocho mapas privados, fuera de la página de EA. No envía mapas al backend. El inspector no necesita emparejamiento.
5. Abre la vista previa. Revisa textos y etiquetas, elimina los mapas si no deseas conservarlos y, cuando estén revisados, marca la casilla y exporta. Comparte únicamente el JSON revisado o su ruta local, nunca cookies, HAR, perfil de Chrome ni HTML completo.

## Qué recoge y qué queda pendiente

Una región seleccionada, como máximo dos contenedores ascendentes, 400 nodos visitados, 120 visibles, profundidad siete y 64 KB de resultado. No recorre `body`; omite formularios, entradas, contenido editable, scripts, iframes y nodos ocultos. Recoge etiquetas, roles permitidos, clases CSS acotadas, texto corto visible, `aria-label`, `aria-busy` y `aria-rowcount`. No recoge atributos arbitrarios, valores de entrada, URLs de imágenes/enlaces, contenido de canvas, almacenamiento ni HTML. No cruza shadow DOM. Los límites y el truncamiento se muestran explícitamente.

Los controles son candidatos con `approved=false`. Su nombre no acredita un efecto seguro. `virtualized`, filtros y página permanecen desconocidos si no hay un perfil que los interprete. Fin de lista y cobertura global no se afirman. Un detector de secretos reduce riesgos, pero no reemplaza la revisión humana de la exportación.

Cada mapa conserva fecha local, referencia de documento y procedencia. La fecha es de lectura del DOM, no de actualización remota de EA. La firma usa estructura, roles y selectores, sin textos personales, saldo ni nombre del club. El perfil queda `proposed`, sin extractores ni transiciones habilitadas. No se ejecuta configuración recibida ni código remoto.

Pendiente de evidencia real: cabecera/cuenta, lista, detalle, principal y un DCP/objetivo. Tras recibirla se contrastarán unicidad, campos, estados de carga y cambios de vista antes de admitir un nuevo origen al inventario. No se ha añadido `observed_page_dom` a la ingesta sin ese contrato. También siguen pendientes fragmentación de listas mayores de 30, planes con checkpoints, actualización automática no conflictiva y motor autónomo en muestra propia. El lector de muestras previo conserva sus límites explícitos; no simula cobertura completa.

## Condiciones y operación

Se consultaron las [reglas de EA](https://help.ea.com/en/articles/ea-sports-fc/fc-rules/) el 18 de octubre de 2026: advierten sobre extensiones y prohíben bots/automatización. El permiso temporal `activeTab` no es una autorización del proveedor. El inspector se limita a observación guiada; no realiza transacciones ni descubre acciones mediante pulsaciones.

El navegador personal nunca se copia a Playwright. Las pruebas usan Chromium y perfiles desechables, mapas sintéticos, PostgreSQL temporal y limpieza por identidad. Una prueba sintética acredita controles del mecanismo, no compatibilidad con EA. No se cambia la principal ni las reglas de admisión/consumo. Un despliegue personal requiere decisión específica, respaldo restaurado aparte y recuperación preparada según [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md).
