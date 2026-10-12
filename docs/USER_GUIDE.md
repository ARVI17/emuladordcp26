# Guía de usuario · FC27

## Entrada y planificador

Al abrir verás **Conexiones y estado del club**. Actualmente muestra **Integración pendiente**, con los permisos y datos que faltan. **Abrir registro local** es una alternativa explícita para revisar lo anterior; el aviso permanece visible y no acredita sincronización EA. El selector de contextos aparece cuando hay más de uno.

En **Planes**, compara cinco objetivos de plantilla o varios DCP, añade acciones/copias concretas y simula. Guarda el borrador, escribe `REVISAR <id>`, reserva y finalmente escribe `APROBAR <id>`. Registra cada resultado con `CONFIRMAR <id> <paso>` después de observarlo. Las operaciones en el juego son manuales. El servidor vuelve a comprobar inventario, reservas, reglas, precios y plazos. Una entrega parcial necesita aceptación específica; cancelar no recupera cartas reales.

**Fichajes** permite preparar fichas públicas asociadas a precios registrados en **Mercado**. La comparación personal espera inventario completo y monedas verificadas. **Mercado** también calcula escenarios hipotéticos y registra compras/anuncios/ventas contrastadas; un anuncio no es venta ni saldo. **Referencias** guarda evidencia revisable de las 50 fuentes y reglas compartidas sin compartir progreso. El recordatorio de revisión no descarga fuentes automáticamente. En Planes también puedes abrir el diario de partidos.

Las lecturas Companion son manuales y muestran hasta 20 candidatos por bloque. Importa la revisión antes de cambiar de bloque. La preparación ADB y los botones de envío de entradas están deshabilitados por falta de permiso aplicable. No se certifica un club completo por capturar muchas páginas.

Consulta [alcance y límites del planificador](FC27_PLANNER.md) para distinguir resultados locales, pruebas sintéticas y conexión real pendiente.

## 1. Elegir la edición y cargar tus jugadores

FC27 es la única edición funcional, sin selector histórico. La instalación empieza vacía; cartas antiguas, saldos y reglas no acreditados se conservan ocultos. Consulta [el contrato de exclusividad](FC27_EXCLUSIVE.md).

En **Club** puedes buscar, filtrar por posición, paginar, crear y corregir cartas. La eliminación es lógica. Los botones CSV/XLSX exportan el inventario disponible de la edición activa.

Para importar:

1. Selecciona un CSV o XLSX con `name,rating,position,league,club,nationality`.
2. Pulsa **Revisar archivo** y comprueba los errores y la muestra.
3. Corrige el archivo si hace falta y repite la revisión.
4. Confirma el mismo archivo. Un cambio de archivo o edición invalida la revisión anterior.

La confirmación tiene un identificador de revisión y repetirla no duplica una importación ya completada. Una nueva revisión intencional de otro archivo se considera otra importación: no hay actualización automática por nombre. No importes repetidamente el club entero para actualizar unos pocos jugadores; edita esas cartas.

### Datos para analizar mejor

Media, posición principal, liga, club y nacionalidad bastan para empezar. Para comparar el encaje, añade posiciones alternativas y atributos:

- Campo: `pace`, `shooting`, `passing`, `dribbling`, `defending`, `physical`.
- Portería: `diving`, `handling`, `kicking`, `reflexes`, `speed`, `positioning`.

Registra PlayStyles, roles, filigranas y pierna mala solo después de comprobarlos en la variante FC27. Las posiciones y atributos ausentes siguen pendientes; no se deducen del nombre del futbolista.

`card_id` debe identificar la variante exacta FC27 con nombre, media, posición y tipo coincidentes con una fuente documentada vigente. Sin esa evidencia la copia queda en cuarentena, fuera de todas las operaciones. `base_card_id` vincula una evolución con su base. Media y puntuación son datos diferentes.

Las cartas sin evidencia de variante quedan en cuarentena; una casilla de revisión no las certifica. La demo se limita a pruebas y nunca representa tu club.

## 2. Analizar y formar tu equipo

**Análisis** muestra profundidad por posición, cartas destacadas, protecciones, cesiones, duplicados y datos pendientes. La sugerencia de formación prioriza cubrir puestos con lo disponible; no demuestra cuál es la táctica más fuerte del juego.

En **Plantillas**:

1. Elige una formación del catálogo FC27 vigente; 4-3-3 y 4-3-3 Holding son distintas.
2. Selecciona enfoque equilibrado, ataque o defensa.
3. Decide si incluir cesiones y posiciones alternativas.
4. Si necesitas, abre las opciones para fijar jugadores en el once o excluirlos.
5. Pulsa **Proponer once y suplentes**.
6. Revisa el campo, los suplentes, las posiciones alternativas utilizadas y **Por qué** en cada carta.
7. Corrige los huecos o datos pendientes. Una propuesta de once completo puede guardarse con nombre.

La recomendación no compra jugadores ni modifica tu inventario. El encaje combina media y atributos registrados con pequeños ajustes por roles/estilos. La química es la suma de la química 0–3 que registraste en cada carta; no recalcula el sistema completo de enlaces del juego.

**Proteger equipo completo** impide consumir sus jugadores en DCP y se suma al candado manual de cada carta. Quitar la protección de una plantilla no elimina la protección individual ni la de otra plantilla. Los jugadores protegidos siguen disponibles para alinearse en tus equipos.

## 3. Galería e historial

La **Galería** es el registro local de versiones obtenidas. Las cartas creadas/importadas se registran al guardarse cuando cumplen los requisitos. **Registrar inventario** incorpora también el historial local que ya existía. No puede reconstruir adquisiciones pasadas que nunca registraste.

Una carta retirada o consumida localmente conserva su entrada histórica. Esto permite usarla en un conjunto de Galería; no la devuelve al inventario jugable. Las cesiones no cuentan. Para una evolución, la app necesita conocer la carta base original o encontrarla en el historial; no sustituye esa información por la media evolucionada.

Puedes conservar conjuntos como borradores con su fuente. Para evaluarlos se necesita una revisión técnica documentada de sus reglas y vigencia; marcar una casilla no los activa. Una vez acreditados, la evaluación indica:

- plazas cubiertas y pendientes;
- cartas disponibles o solo históricas;
- puntos conocidos y puntos pendientes;
- etiquetas aplicables y grado, cuando todas las condiciones necesarias están verificadas.

Corregir puntos actualiza las copias locales de esa variante. No se aplican puntuaciones oficiales supuestas; la tabla base no acreditada se retiró de Novedades.

La Galería local no se sincroniza con la Galería de EA ni cobra sus recompensas. Los conjuntos personalizados o importados deben contrastarse con las reglas vigentes del juego.

## 4. Evoluciones con caminos y cadenas

En **Evoluciones**, las definiciones introducidas manualmente quedan como borradores hasta acreditar edición, requisitos, caminos y vigencia. Actualmente no hay publicaciones activas cargadas ni un proveedor aprobado que las suministre.

Elige una carta del club y hasta cinco evoluciones distintas, en el orden deseado. Cada paso puede seleccionar un camino. La vista previa comprueba elegibilidad sobre el resultado del paso anterior: media, posiciones, atributos máximos, estilos, estrellas, préstamo y caducidad.

Si falta un atributo necesario, la app indica que no puede verificarlo. Si la cadena deja de cumplir una condición, se detiene con el motivo. Los topes limitan las mejoras, y un rol ya conocido con mayor familiaridad no se rebaja.

La simulación muestra antes/después, no aplica la evolución a tu carta ni al juego. Después de completar una evolución por tu cuenta, corrige la carta en Club con sus datos reales.

## 5. DCP e historial de entregas

Crear un desafío o leer sus requisitos conserva un borrador. Solo una definición FC27 acreditada y vigente permite calcular. Los motores admiten estos formatos:

- **Tradicional:** tamaño, media, química registrada, posiciones, restricciones de ligas/clubes/países, cartas especiales, presupuesto y otras reglas admitidas.
- **Puntuación:** objetivo de puntos, media mínima por carta y máximo de cartas por entrega. Se usan únicamente puntuaciones positivas revisadas y se admiten entregas parciales.

Optimizar no modifica el inventario. Compara alternativas y comprueba los nombres. El valor de las cartas es la suma de `price`; el criterio interno que preserva cartas valiosas aparece separado del precio.

**Confirmar entrega** registra el consumo local después de una revalidación. No pulsa entregar en Companion. Las cartas protegidas, cedidas, no revisadas, de otra edición, consumidas o repetidas por ID se rechazan. En el formato por puntos, el progreso procede de las entregas confirmadas, no de un contador editable.

El historial permite **restaurar** una entrega local. La app comprueba que cada carta siga perteneciendo a ese consumo y restaura toda la operación de manera atómica. En puntos, descuenta solo la aportación de esa entrega. Esta restauración no recupera una carta que ya entregaste realmente en EA.

Una vez hay entregas activas no puedes cambiar las reglas del segmento. Restaura primero lo necesario si estás corrigiendo una prueba local. Los duplicados son copias diferentes con IDs diferentes; reenviar el mismo ID nunca cuenta como otra copia.

## 6. Novedades y contenido que va cambiando

**Actualizar noticias** descubre enlaces en fuentes públicas fijas de EA. Solo aparecen como noticias verificadas los artículos con edición, fecha editorial y evidencia vigente; los demás quedan pendientes. No inicia sesión ni consulta tu cuenta. Si no hay red, EA rechaza la petición o cambia el HTML, se conserva la información anterior.

Para agregar o corregir conjuntos/evoluciones, importa un paquete JSON en **Novedades**. Revisa edición, fecha y contenido antes de confirmar. La confirmación exige el mismo hash del paquete revisado; repetir un paquete ya importado no vuelve a aplicar una versión antigua sobre cambios posteriores. El `slug` identifica cada definición para actualizarla.

Un titular nuevo no modifica por sí solo las reglas del solver. Los DCP nuevos se introducen y revisan en DCP. El proyecto no ofrece un inventario completo y automático del contenido de temporada. Consulta [FC27_UPGRADE.md](FC27_UPGRADE.md) para el formato de paquetes.

## Companion y lectura del inventario

Inicia Android y la sesión de Companion manualmente. En **Emulador**, conecta el dispositivo y abre **Mi club → Futbolistas**. El panel puede leer la jerarquía accesible; si no existe, recurre a OCR conservador. Ninguna captura se importa automáticamente.

La compatibilidad con una versión real FC27 sigue pendiente. Puedes conservar lecturas para revisión, pero sus importaciones quedan en cuarentena. Los toques, deslizamientos y avances automáticos están deshabilitados; cambia de página manualmente en el dispositivo. La app valida dispositivo, resolución y cambio de página. Una lectura admite 50 páginas/1000 candidatos; **Continuar en un lote nuevo** conserva una referencia para evitar repetir la página límite.

Corrige los candidatos y selecciona solo los comprobados. No se aceptan nombres «Por revisar» ni valores de relleno. La importación exige `IMPORTAR <id>`, hasta 500 cartas por solicitud; archivar los nombres exactos de la demo exige `REEMPLAZAR DEMO <id>`. No se eliminan físicamente las cartas. Una sesión cerrada o una selección ya importada no puede reutilizarse para crear copias inadvertidas.

Para depuración inalámbrica de Android, el puerto de emparejamiento puede ser distinto del puerto de conexión. El código ADB de seis dígitos se utiliza una sola vez y no se persiste. La aplicación no pide códigos ni contraseñas de EA.

### Preparación asistida pendiente

El motor conserva planes revisables, calibración y cancelación para pruebas aisladas. La aplicación no tiene permiso aplicable ni compatibilidad de dispositivo acreditada para ejecutar pulsaciones contra Companion. Crear o revisar un plan no habilita su ejecución. La entrega, compras y ventas nunca se automatizan.

## Objetivos, IA, Ajustes y respaldo

Objetivos conserva progreso y recordatorios locales. El chat muestra resúmenes FC27 redactados desde cantidades verificadas. Ollama puede elegir el enfoque, pero no redacta hechos libres ni ejecuta cambios; se conserva solo la intención de la pregunta. Ajustes permite corregir perfil/presupuesto y revisar capturas OCR. El tema se conserva en el navegador.

Respaldar antes de actualizar protege todo el historial, no solo el inventario exportado. Los scripts de PowerShell resuelven la configuración de Compose; la restauración exige un dump dentro de `backups`, crea una copia previa y detiene la API durante el proceso. Un CSV es útil para intercambiar jugadores, pero no reemplaza un respaldo de PostgreSQL.
