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

En **Emulador**, conecta el dispositivo y abre manualmente **Mi club → Futbolistas**. Pulsa **Nueva lectura** y después **Leer página actual**. En Companion la jerarquía de accesibilidad permite leer nombre, media y posición de hasta 20 filas, incluso si algunas quedan fuera del área visible; si no está disponible, se usa OCR conservador. **Avanzar y leer siguiente** desplaza la lista, valida el botón, pulsa únicamente `Siguiente` y comprueba que los jugadores cambiaron. Una página idéntica no se duplica.

En teléfonos Android modernos, activa **Opciones de desarrollador > Depuración inalámbrica > Emparejar dispositivo con código**. Introduce el IP:puerto de emparejamiento y los seis dígitos en el panel; el código no se guarda. Luego copia a **Conectar** el IP:puerto de conexión que muestra Android, que normalmente es diferente.

La importación normal exige `IMPORTAR <id>`. Cada solicitud acepta hasta 500 cartas y conserva sus `candidate_id`; si quedan candidatos, la lectura continúa en `review` para otro grupo. La opción de reemplazo archiva exclusivamente los nombres exactos de las 132 cartas demostrativas y exige `REEMPLAZAR DEMO <id>`; no borra físicamente cartas ni toca entradas manuales con otros nombres. Las imágenes y el XML de accesibilidad nunca se guardan. Una sesión admite hasta 50 páginas y 1000 candidatos; **Continuar en un lote nuevo** evita repetir la página límite. La revisión se pagina de 20 en 20 para no crear miles de controles DOM y reducir RAM, y las cartas empiezan desmarcadas. Companion no expone de forma textual y fiable liga, club, nacionalidad, tipo, transferibilidad o precio: corrige esos campos y selecciona solo las cartas comprobadas antes de importar.

Para leer un segmento, muéstralo en Companion y pulsa **Leer requisitos DCP**. La aplicación intenta reconocer tamaño, media, química, raros y otros conteos. El resultado es un borrador: revisa sus requisitos en DCP antes de optimizar.

## Objetivos, IA y Ajustes

Objetivos admite alta, progreso incremental y finalización. Las evoluciones son objetivos con categoría propia. IA conserva el historial local y se degrada con un mensaje claro si Ollama no responde. Ajustes permite editar perfil, presupuesto, plataforma, nivel de riesgo, tema, revisión OCR y restauración de entregas.

Antes de eliminar o consumir cartas, la interfaz solicita confirmación. Una carta con el indicador de candado no entra en soluciones DCP.
