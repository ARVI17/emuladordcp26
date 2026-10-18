# Lectura visual asistida de FC27

## Lector estructurado, Galería y utilidades (18-oct-2026)

Base comprobada: `4f8eded842682a98ba8f9678da5c01feb00547c2`; rama de ampliación `agent/fc27-dom-gallery`. La inspección local encontró la pestaña «FC27» en ChatGPT, no en EA, y ninguna muestra de lista/ficha/DCP o exportación legítima en los archivos disponibles. No se inspeccionó el perfil privado de Chrome. **El extractor EA real sigue pendiente de estructura observada y permiso aplicable.** El recorrido compilado usa HTML sintético propio; no certifica el hito con el club real.

### Instalar y emparejar

Desde la raíz de esta rama:

```powershell
cd extension
npm.cmd ci
npm.cmd run check
npm.cmd run build
```

En `chrome://extensions`, habilita modo desarrollador y **Cargar descomprimida** → `extension/.output/chrome-mv3`. Es un cliente del mismo backend; necesita esta rama con migración `0018`. Cargarlo no actualiza la instalación personal. No requiere scripts remotos, Native Messaging ni copiar el perfil.

Dependencias principales comprobadas en sus paquetes instalados: WXT 0.21.4 y Zod 3.25.76 (MIT), Playwright 1.62.1 (Apache-2.0). El build local también se empaquetó en `state/club-lab-reader-0.1.0.zip`, fuera de Git.

En **Mi cuenta**, selecciona explícitamente un contexto asistido. Copia el ID de extensión mostrado en su panel a **Lector estructurado**, confirma `EMPAREJAR LECTOR` y copia ID/código de emparejamiento al panel. El código dura tres minutos/cinco intentos; la credencial local dura como máximo doce horas, ligada a sesión/contexto/generación. Nunca es una credencial EA.

**Activar lector en esta pestaña** reconoce solamente el contrato semántico propio `sample-v1`, servido por loopback en `/reader-sample.html`: raíz `data-club-lab-sample="1"`, edición/fuente/vista y campos hoja `data-field`. No son selectores de EA. Admite `synthetic_dom` o `user_export_dom`; una exportación legítima necesita adaptación explícita a este contrato. Lista/ficha/plantilla/resultado están representados. DCP y objetivos conservan el flujo de transcripción revisada existente.

Tú navegas y cargas páginas; el lector observa cambios visibles sin emitir acciones. **Reintentar envío**, **Analizar lo leído**, **Pausar** y **Desconectar** son explícitos. Los lotes se revisan en Club Lab con `REVISAR LOTE DOM`, sin escribir cada carta otra vez. Los hechos de EA no se actualizan automáticamente hasta contrastar un extractor. Las propuestas usan las copias revisadas, mantienen principal/reservas y muestran cobertura parcial.

El **Diagnóstico mínimo** de la ruta oficial muestra únicamente hasta 240 caracteres seleccionados por el usuario, etiqueta del elemento y ocho etiquetas hijas. Excluye inputs y pantallas/patrones sensibles; no se envía automáticamente al backend. No contiene HTML completo, cookies, tokens, URLs de imágenes o IDs EA. Es una ayuda inicial, insuficiente por sí sola para certificar identidades, lista o reglas.

### Transporte y persistencia

Rutas: `/reader/pairings`, `/claim`, `/events`, `/events/{id}/review`, `/status`, `/proposal`, `/grants/{id}/revoke`, `/disconnect`. Cookie local/CSRF aprueban y revisan; la credencial de extensión solo ingiere candidatas, consulta propuestas y se revoca. Se validan Host/Origin, extensión, frame/pestaña/documento/nonce, contexto, tamaños y esquema. No se elimina admisión ORM ni se registra un adaptador ficticio.

MV3 usa WXT/TypeScript/Zod, `activeTab`, `scripting`, `storage`, `sidePanel`, y permisos de transporte solo a `http://localhost/*` y `http://127.0.0.1/*`; ningún permiso persistente sobre EA. `storage.local` y `storage.session` se restringen a contextos privilegiados. Cola: 100 eventos/512 KB; lote: 30 cartas/128 KB; servidor: 30 eventos nuevos/minuto. Persiste ID/hash/secuencia/fecha antes de enviar y elimina solo tras acuse. Saturación/error se muestran sin descarte silencioso.

`ReaderGrant`/`ReaderEvent` (`0018`) conservan concesiones locales y recibos atómicos. Revisión y recibo original son independientes: reintentar devuelve el mismo recibo incluso después de revisar. No renueva la fecha. Más de 30 minutos o secuencia antigua produce historial; no reemplaza evidencia reciente ni reactiva consumidas. Otra lectura de nombre/media/posición iguales conserva la ambigüedad de copia del flujo asistido. No acredita IDs de copia EA.

### Cálculos nuevos

Galería v2 es optativa por definición; v1 conserva puntos fijos. V2 declara multiplicidad por futbolista/variante/entrada, porcentajes en puntos básicos, tramos, subtotal coincidente, suelo por etiqueta y suma aditiva. Admite primer propietario, posición, pie débil, filigranas, nivel holográfico, grupos y diversidad. CP-SAT y comprobador independiente usan enteros. Ejemplo **sintético**: `1000,1000,100,100`, 10 % solo sobre las dos últimas → bono **20**, total **2220**. La separación holográfica está probada con un ID compartido sintético; no demuestra colisión real de IDs EA.

Grado obtenido, premio reclamado y fichas potenciales son distintos. Premios acumulados ficticios `D=0,C=5,B=15,A=30,S=50`: mejorar B→S aporta **35**. No se inventa saldo disponible/gastado. `/gallery/local-scenarios` expone hipótesis sin convertir definiciones pendientes en activas. `/gallery/route-preview` exige progreso declarado, mercado, cotizaciones vigentes y base/puntos documentados de cada adquisición.

La ruta explora hasta diez candidatas compartidas/ocho conjuntos durante ocho segundos. Su secuencia conservadora compra toda la cesta antes de vender: capital máximo igual a compras brutas, sin prometer capital mínimo entre todas las secuencias. Ejemplo **sintético**: compra 10000, venta 9800, comisión asumida 5 % → ingreso 9310, gasto neto 690, capital 10000. Una adquisición compartida se paga una vez; retenerla no descuenta una venta. Valor residual, ingreso previsto y resultado realizado van separados; ventas pendientes no aumentan monedas. Simular no crea compras propias ni planes ejecutables.

DCP añade filtros de primer propietario/holografía/cesión/Evo, `/dcp/templates` y `locked_ids`. Reutilizar por API verifica huella de requisitos y recalcula; aplicar filtros en UI solo modifica filtros. **Sustituir solo esta carta** exige las demás y revalida protecciones. `/objective-journal/{uuid}` guarda tareas declaradas por partido, idempotencia, revisión optimista e historial de correcciones. Corregir reemplaza ese partido sin incrementar progreso EA ni certificar condiciones de composición.

### Matriz funcional

Fuentes consultadas el 18-oct-2026: funciones publicadas de [Paletools](https://pale.tools/) y [condiciones](https://pale.tools/terms.html); [etiquetas FUT Gallery FC27](https://www.fut.gg/fut-gallery/tags/) (página fechada 8-oct-2026). No se ejecutó Paletools ni se acreditó su última versión instalada. La fórmula publicada es evidencia FUT.GG, no oficial EA. [Stormstrike](https://stormstrike.gg/terms) restringe scraping/reutilización sin permiso; no se añadió su recolector. [Reglas EA](https://help.ea.com/es/articles/ea-sports-fc/fc-rules/) y [Community API](https://help.ea.com/es/articles/ea-sports-fc/community-api/) no transfieren permisos de socios a Club Lab. No se copió código/arte propietario ni se atribuyeron acciones al Reel no disponible.

| Función / evidencia | Equivalente y mejora | Datos / riesgo | Aceptación y estado |
| --- | --- | --- | --- |
| Lector lateral, referencia Paletools | MV3 → cola → API → copias revisadas → cinco perfiles | DOM/copia/cuenta reales desconocidos | Chromium/PostgreSQL con muestra sintética; **parcial, acceso real bloqueado** |
| Principal/alternativas, base 4f8eded | Reutiliza protección, reservas y comprobador | Ambigüedad excluida; jugar no consume | Huella y protecciones en regresiones; **existente probado** |
| Filtros/plantillas/reemplazo DCP | Configuraciones versionadas, fijar y sustituir | Requisitos revisados; sin autorización de consumo | Reglas cambiadas, reemplazo y protegidas; **nuevo probado** |
| DCP tradicional/puntuación/conjunto | Solver, restante y presupuesto conjunto existentes | Media aproximada; espacio limitado | Suite optimizador/conjunto; **existente probado** |
| Bonificaciones FUT.GG FC27 | V2 optativa, tramos/grupos/redondeo/multiplicidad | Fuente/puntos/atributos; escenarios no oficiales | 20 puntos, nulos, tramos, v1 intacta; **nuevo probado** |
| Fichas/presupuesto FUT Gallery | Progreso declarado y cesta compartida | Sin saldo remoto; capital conservador | 35 fichas, 10000/690; **nuevo probado**, precios reales **pendientes** |
| Objetivos y práctica | Generador/guía existentes + diario corregible | Modalidad/dificultad/resultados declarados | Correcciones sin doble registro/progreso; **nuevo probado** |
| Evos, comparador, pendientes | Se conservan motores/pantallas | Base, vencimiento y desconocidos | Regresiones existentes; **parcial**, sin lector DOM de tareas/Evos/sobres |
| Soluciones externas/atajos/sobres | CSV, navegación y comparación existentes | No transformar propuestas en propiedad | Nuevos importador de soluciones, atajos especializados y organización estructurada de sobres: **pendientes**, sin botones vacíos |
| Recolector público | Referencias/consulta manual existentes | Licencia/acceso/edición/frescura | Sin nuevo crawler restringido; **bloqueado por acceso** |
| Resultado de aplicación | Guía manual y conciliación visual existentes | Declaración no es recibo EA | Flujo visual probado; resultado DOM real **pendiente** |
| Compras/ventas/entregas/login/sobres | Sin ejecución remota | Fuera de autorización | **Excluido por automatización** |

La inspección permitida de una lista, una ficha y un DCP/objetivo sigue siendo necesaria para completar el primer hito real. Nuevos perfiles de sacrificio DCP e importador de soluciones siguen pendientes. Resultados exactos y límites: [TESTING.md](TESTING.md).

La aplicación admite un origen de propiedad **observado y revisado por el usuario**, separado del catálogo y del lector autorizado. No hay adaptadores de producción ni escritura en EA. Una sesión del navegador, el nombre del contexto y una imagen compartida no autentican la cuenta ni sus copias.

## Recorrido disponible

1. En **Mi cuenta**, crea un contexto de lectura para tu club. Otros clubes y el registro histórico permanecen separados.
2. Abre tú la Web App oficial. Pulsa **Compartir pestaña de FC27**, elige la pestaña en el navegador y revisa la vista previa. Alternativamente, adjunta PNG/JPEG/WebP.
3. Selecciona el ámbito, indica página y filtros, y pulsa **Leer pantalla**. Solo esa acción envía una imagen al OCR local. Puedes seleccionar una región; primero se examina la pantalla completa para detectar contenido sensible.
4. **Revisar lectura** permite corregir las candidatas, conservar desconocidos y vincular una nueva observación a una copia local existente. **Guardar observación** requiere revisión de edición y una frase explícita. No crea cartas por mostrar el vídeo.
5. Para **Registrar mi principal**, lee sus páginas, asigna puestos (`POR-1`, `MC-1`, `BENCH-1`, `RESERVE-1`, etc.) y revisa once, banquillo y reservas. La selección conserva una instantánea y bloqueos del servidor. Un cambio posterior observado pide revisión y conserva las protecciones anteriores.
6. Lee un **Objetivo**, revisa texto, condiciones, acciones, modalidad y vencimiento con el editor existente. **Crear plantilla para este objetivo** utiliza las copias revisadas y aptas. La alternativa tiene otro ID y no modifica la principal ni el progreso.
7. **Preparar guía manual** conserva las cartas y puestos de esa propuesta. Revisa, aprueba con `APROBAR GUIA <id>` y sigue los pasos en EA manualmente. La guía solo prepara una plantilla alternativa para jugar, sin compras, ventas, entregas ni activación de principal.
8. **Comprobar resultado** prepara una lectura nueva. Revisa las pantallas del resultado, selecciona sus páginas y compara. Solo una composición completa coincidente permite **Conciliar observación respaldada**. El recibo sigue siendo visual revisado, nunca confirmación del proveedor ni identificación inequívoca de copias EA.

El permiso se solicita en cada nueva sesión de compartir. El indicador permanece al navegar por la aplicación; cerrar/reabrir no restaura captura. Pausar impide lecturas; detener finaliza las pistas. En navegadores sin captura de pestañas se conserva la alternativa de imágenes. El origen HTTP interno de las pruebas Docker usa esa alternativa; localhost es el acceso personal previsto.

## Evidencia y cobertura

`CaptureSession`, `VisualReading` y `VisualCopy` (Alembic `0017`) conservan fechas originales, contexto, sesión, página, filtros, candidatas OCR, valores revisados, campos desconocidos, conflictos y decisiones. Nunca almacenan imágenes, vídeo, audio ni credenciales. Los originales son datos estructurados mínimos; el texto completo solo se conserva para un objetivo o DCP que pasó el detector de contenido sensible.

El OCR reconoce filas españolas `media posición nombre` o esos elementos en líneas sucesivas, y propone nombre de club y monedas cuando están rotulados. Puede proponer tipos/cantidades de artículos sin asignar y atributos rotulados de una ficha individual. La confusión OCR `El/EL` → `EI` se muestra con baja confianza y conserva el valor original; exige revisión. Las vistas gráficas que el extractor no reconoce necesitan una captura más legible, una región o una ficha ampliada. No se ha validado todavía una captura personal de EA del propietario.

La revisión puede aportar metadatos visibles y corregir OCR. Cada dato sigue etiquetado visual revisado, no verificado por proveedor. Los desconocidos se exponen como `null`; los valores técnicos internos vacíos no son hechos. IDs de jugador, candidata, lectura y variante local no se presentan como IDs EA.

La admisión ORM une la prueba visual interna a su lectura revisada y contexto antes de contar, paginar o cargar relaciones. Declarar `verified=true`, copiar una variante del catálogo o cambiar `data_source` por HTTP no acredita propiedad visual. El contexto asistido solo muestra esas observaciones. FC26 no participa.

Se deduplican imágenes y páginas normalizadas sin renovar fechas. Una etiqueta de página distinta puede mostrar otra copia legítima; nombre, media y posición coincidentes forman un grupo conservador aunque cambie la etiqueta de variante. El grupo queda fuera del solver hasta resolver si es la misma copia o son copias distintas. La decisión es humana y se conserva; no acredita IDs EA. Una lectura vieja nunca reactiva cartas retiradas. Las candidatas ambiguas de una carta protegida heredan exclusión de consumo.

La cobertura siempre es parcial: páginas observadas/revisadas, filtros, ubicaciones pendientes y conflictos. Ni una página ni la declaración de fin certifican todo el club. Un cambio visible de nombre del club exige otro contexto. Cuando la identidad no está visible no puede detectarse automáticamente un cambio de cuenta: el usuario debe seleccionar el contexto correcto.

## DCP, Galería y otras funciones

En modo asistido, **DCP observados** simula reglas de una lectura revisada con el solver y su validador independiente. Conserva filtros, protecciones, reservas y exclusión por metadatos necesarios desconocidos. No habilita las rutas antiguas de confirmación ni ADB. Los comparadores no representables quedan pendientes; una lista vacía no demuestra imposibilidad de un inventario completo. El progreso anterior de un DCP no se deduce de sus cartas actuales.

Galería permite registrar explícitamente historia local de variantes observadas con condiciones de cesión/Evo conocidas. No reconstruye adquisiciones anteriores, no consume cartas ni altera recompensas. Sus conjuntos siguen necesitando reglas documentadas; los puntos desconocidos permanecen desconocidos. Las reservas incompatibles siguen excluyendo consumos, pero no impiden por sí mismas este registro histórico no consumptivo.

Análisis y plantillas usan los atributos conocidos y explican las limitaciones. Mercado y evoluciones mantienen sus controles de variante, precio fechado, mercado, presupuesto y reglas. La captura no proporciona datos ausentes ni refresca fuentes silenciosamente; las operaciones sin evidencia suficiente permanecen pendientes.

## Aprobación, incertidumbre y privacidad

La guía liga contexto, entrada, inventario, principal, objetivos/reglas, reservas, cartas/puestos, límite económico cero y vencimiento. Revalida antes de aprobar, iniciar y avanzar cada paso. Preparar/aprobar no consume cartas ni resta monedas. Estados: borrador, revisado, aprobado, pendiente de aplicar, en comprobación, resultado declarado/observado, conciliado, pausado, fallido declarado, incierto y cancelado.

**Ya lo hice** es una declaración manual. Saldo aislado, ausencia de una carta o una pantalla incompleta no prueban una venta/entrega. Los recibos son idempotentes. Una guía empezada con resultado incierto impide repetir la misma propuesta, incluso si se cancela localmente. Se puede observar un resultado después de caducar una aprobación; eso conserva solo hechos visuales y no permite continuar pasos con aquella aprobación. Cancelar/restaurar localmente nunca revierte EA.

Límites: 10 MB por imagen, dimensiones/píxeles y timeout del OCR existente, exclusión de OCR concurrente, 50 páginas por sesión, sesión de 30 minutos y como máximo 20 formularios visibles de revisión. Imágenes: retención en servidor **cero**. La vista previa queda solo en memoria del navegador y se borra al detener o cerrar. `ASSISTED_DRAFT_RETENTION_MINUTES` (30 por defecto) borra el contenido de borradores vencidos al iniciar otra captura; **Borrar datos de captura** permite hacerlo antes. Las observaciones ya revisadas son historial personal persistente en PostgreSQL y no se borran al cerrar la captura.

El detector de credenciales/pantallas ajenas es conservador y puede fallar. Nunca compartas una pantalla de acceso. Si detecta un riesgo, no guarda ni devuelve ese texto y exige seleccionar otra vez. Imágenes, inventarios, bases y respaldos no se incluyen en Git.

## Verificación y fuentes

`test_assisted.py` usa candidatas sintéticas y PostgreSQL aislado, sin testigos de catálogo. `assisted.spec.ts` genera texto sintético en PNG y recorre el OCR real, API y UI en Chromium móvil/escritorio. Estas pruebas no acreditan captura personal, permiso real del selector del sistema, integración remota ni escritura en EA. Los resultados se registran en `docs/TESTING.md` y los artefactos privados en `state/sprints/`.

Documentación revisada el 12 de octubre de 2026: [W3C Screen Capture](https://www.w3.org/TR/screen-capture/) exige elección y permiso por sesión; [EA Community API](https://help.ea.com/es/articles/ea-sports-fc/community-api/) restringe su conexión oficial a socios aprobados. Ninguna de esas capacidades convierte esta aplicación en socio autorizado.
