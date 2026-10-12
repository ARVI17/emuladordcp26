# Guía de usuario

## Inicio y Club

Inicio resume monedas, cartas, protegidos, duplicados, DCP y vencimientos. Club permite búsqueda por nombre/club/país, filtro de posición, alta, edición, protección y eliminación lógica. La exportación CSV/XLSX incluye solo cartas disponibles.

Para importar, elige CSV/XLSX, pulsa **Revisar archivo** y examina el conteo y la muestra. **Confirmar importación** es la única acción que escribe datos. También puedes registrar todas las cartas manualmente.

## Plantillas

La plantilla principal aparece con media y química. **Recomendar** elige el jugador mejor valorado disponible por puesto para un 4-3-3; después puede guardarse. Es posible duplicar una plantilla o proteger/desproteger todas sus cartas.

## DCP y duplicados

Crea un DCP básico o abre uno demostrativo. Optimizar solo simula. Compara coste, media, química y uso de duplicados. La entrega requiere confirmación explícita y rechaza protegidos o restricciones incumplidas. Conserva el ID mostrado si quieres restaurarla.

Duplicados enumera intransferibles, sugiere segmentos compatibles por media y permite marcar una carta como utilizada. El motor les aplica una bonificación de coste para escogerlos antes cuando las restricciones lo permiten.

## Preparar una combinación en el emulador

La automatización es asistida: coloca jugadores, pero nunca pulsa el botón de entrega final.

1. Inicia un teléfono/emulador Android con ADB por TCP. En **Emulador**, conecta su dirección (normalmente `host.docker.internal:5555`).
2. Abre manualmente en el dispositivo la pantalla del segmento DCP y no introduzcas credenciales en la aplicación web.
3. Toma una captura. Registra el ancho, alto y las coordenadas de: abrir búsqueda, campo de texto, primer resultado y agregar jugador. Guarda la calibración.
4. En **DCP**, optimiza y pulsa **Preparar en emulador** sobre la combinación elegida.
5. Vuelve a **Emulador**, pulsa **Preparar pasos**, revisa la cantidad y escribe exactamente `PREPARAR <id>` para iniciar.
6. Observa el progreso, cancela si la pantalla no coincide y verifica manualmente los once jugadores. Solo tú puedes aceptar la entrega final en el dispositivo.

La calibración depende de la resolución, escala, orientación e interfaz visibles. Repítela si cualquiera cambia. **Inspeccionar OCR** ayuda a confirmar la pantalla, pero no garantiza que el dispositivo esté en el lugar correcto. Los estados del plan son `draft`, `prepared`, `running`, `completed`, `failed` y `cancelled`; `completed` significa que acabaron los pasos de preparación, no que se entregó el DCP.

## Sincronizar el club mostrado en Companion

En **Emulador**, conecta el dispositivo y abre manualmente **Mi club → Futbolistas**. Pulsa **Nueva lectura**. Cuando quieras traer lo que está mostrando Companion, pulsa **Actualizar desde Companion**: cada pulsación hace exactamente una lectura de la jerarquía visible, sin temporizador, capturas, OCR, toques ni Ollama. Si la pantalla no tiene el título `Futb. de Mi Club`, no modifica la sesión; una página idéntica tampoco se duplica. Cambia de página manualmente en Companion y vuelve a pulsar el botón para acumular la siguiente.

**Leer página actual** sigue disponible cuando necesitas el flujo con respaldo OCR, y **Avanzar y leer siguiente** puede desplazar la lista, validar el botón, pulsar únicamente `Siguiente` y comprobar que los jugadores cambiaron. Estas dos acciones son más intensivas y deben usarse de forma consciente. **Actualizar revisión** solo recarga desde la base local la sesión y sus 20 candidatos visibles; no vuelve a leer Companion.

En teléfonos Android modernos, activa **Opciones de desarrollador > Depuración inalámbrica > Emparejar dispositivo con código**. Introduce el IP:puerto de emparejamiento y los seis dígitos en el panel; el código no se guarda. Luego copia a **Conectar** el IP:puerto de conexión que muestra Android, que normalmente es diferente.

La importación detallada exige `IMPORTAR <id>` y acepta hasta 500 seleccionadas. Para reunir todos los lotes sin navegar página por página, revisa el resumen **Carga completa sin duplicados** y escribe `IMPORTAR TODO EL CLUB`: el servidor procesa hasta 5000 pendientes, pero el navegador sigue conservando solo 20 formularios. Antes de crear cartas compara nombre normalizado, media y posición con los demás lotes y con cartas activas o ya usadas. Las incompletas no se importan. Los campos que Companion no muestra de forma fiable —liga, club, nacionalidad, tipo, transferibilidad y precio— quedan como no disponibles hasta que los corrijas.

Una sesión admite hasta 50 páginas y 1000 candidatos; **Continuar en un lote nuevo** evita repetir la página límite. Confirmar un DCP retira de las lecturas pendientes las identidades de las cartas consumidas para que una captura anterior no las vuelva a importar. La opción de reemplazo demo permanece limitada a los 132 nombres deterministas y exige `REEMPLAZAR DEMO <id>`.

Para actualizar un segmento, muéstralo en Companion y pulsa **Leer requisitos DCP**. Revisa el nombre y los requisitos, escribe `ACTUALIZAR DCP` y guarda: si el nombre ya existe actualiza su segmento pendiente en lugar de duplicarlo. Para objetivos, abre la pantalla correspondiente, pulsa **Leer objetivos visibles**, revisa nombre/progreso/meta y confirma con `ACTUALIZAR OBJETIVOS`. Solo se actualizan filas visibles; las ausentes no se eliminan. Ninguno de estos flujos afirma sincronización oficial con EA.

## Objetivos, IA y Ajustes

Objetivos admite alta, progreso incremental y finalización. Las evoluciones son objetivos con categoría propia. En **IA**, el Análisis DCP guiado pregunta por segmento, conservación de titulares y cantidad de propuestas; OR-Tools calcula sin consumir cartas incluso si Ollama no responde. Revisa una propuesta y escribe `CREAR PLAN <segmento>` para crear solo su borrador. El chat conserva historial local y usa un resumen controlado para explicar datos. Ajustes permite editar perfil, presupuesto, plataforma, nivel de riesgo, tema, revisión OCR y restauración de entregas.

Antes de eliminar o consumir cartas, la interfaz solicita confirmación. Una carta con el indicador de candado no entra en soluciones DCP.
