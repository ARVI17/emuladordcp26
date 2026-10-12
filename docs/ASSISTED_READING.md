# Lectura visual asistida de FC27

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
