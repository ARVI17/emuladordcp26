# Guía de usuario · FC27

## 1. Elegir la edición y cargar tus jugadores

Selecciona **FC27** en la cabecera. FC26 conserva los datos anteriores en un archivo separado; cambiar de edición no convierte cartas ni mezcla sus DCP o plantillas. Una instalación nueva empieza vacía salvo que se haya configurado expresamente una demo antes del primer arranque.

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

PlayStyles, PlayStyles+, roles, filigranas y pierna mala son opcionales. FC27 admite hasta tres PlayStyles+ por carta. Si utilizas CSV/XLSX, listas y objetos van como JSON en la celda; exporta una carta completa para ver el formato.

`card_id` identifica una versión concreta y `base_card_id` vincula una evolución con su versión original. No inventes esos valores: sin identificadores la app usa una identidad conservadora por datos/nombre y puede necesitar corrección en homónimos o abreviaturas. La puntuación de carta se introduce después de comprobarla en el juego. **Media y puntuación son campos diferentes.**

Las cartas por revisar quedan fuera de las recomendaciones normales y de los DCP. Marca como revisados únicamente los datos que hayas comprobado. La demo, cuando se solicita, está formada por jugadores y competiciones ficticios.

## 2. Analizar y formar tu equipo

**Análisis** muestra profundidad por posición, cartas destacadas, protecciones, cesiones, duplicados y datos pendientes. La sugerencia de formación prioriza cubrir puestos con lo disponible; no demuestra cuál es la táctica más fuerte del juego.

En **Plantillas**:

1. Elige 4-3-3, 4-4-2, 4-2-3-1, 4-1-2-1-2 o 3-5-2.
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

Puedes crear y editar conjuntos por liga, club, país, tipo, media y holográficos. Los campos avanzados permiten etiquetas y umbrales de grado. Revisa las reglas antes de marcar el conjunto como comprobado. La evaluación indica:

- plazas cubiertas y pendientes;
- cartas disponibles o solo históricas;
- puntos conocidos y puntos pendientes;
- etiquetas aplicables y grado, cuando todas las condiciones necesarias están verificadas.

Corregir puntos de una entrada actualiza las copias locales de esa misma versión. Una carta sin puntuación revisada nunca recibe puntos oficiales supuestos. La tabla base en Novedades es una referencia; no incorpora automáticamente todas las bonificaciones.

La Galería local no se sincroniza con la Galería de EA ni cobra sus recompensas. Los conjuntos personalizados o importados deben contrastarse con las reglas vigentes del juego.

## 4. Evoluciones con caminos y cadenas

En **Evoluciones**, registra una definición con requisitos, caminos de mejora, topes y fecha de caducidad si corresponde. Añade la fuente y marca la revisión cuando hayas comprobado todos los campos. Las antiguas tareas de categoría «Evolución» en Objetivos siguen siendo recordatorios y no se convierten por sí solas en definiciones de mejoras.

Elige una carta del club y hasta cinco evoluciones distintas, en el orden deseado. Cada paso puede seleccionar un camino. La vista previa comprueba elegibilidad sobre el resultado del paso anterior: media, posiciones, atributos máximos, estilos, estrellas, préstamo y caducidad.

Si falta un atributo necesario, la app indica que no puede verificarlo. Si la cadena deja de cumplir una condición, se detiene con el motivo. Los topes limitan las mejoras, y un rol ya conocido con mayor familiaridad no se rebaja.

La simulación muestra antes/después, no aplica la evolución a tu carta ni al juego. Después de completar una evolución por tu cuenta, corrige la carta en Club con sus datos reales.

## 5. DCP e historial de entregas

Crea un desafío y sus segmentos, o revisa un borrador leído desde Companion. El editor permite dos formatos:

- **Tradicional:** tamaño, media, química registrada, posiciones, restricciones de ligas/clubes/países, cartas especiales, presupuesto y otras reglas admitidas.
- **Puntuación:** objetivo de puntos, media mínima por carta y máximo de cartas por entrega. Se usan únicamente puntuaciones positivas revisadas y se admiten entregas parciales.

Optimizar no modifica el inventario. Compara alternativas y comprueba los nombres. El valor de las cartas es la suma de `price`; el criterio interno que preserva cartas valiosas aparece separado del precio.

**Confirmar entrega** registra el consumo local después de una revalidación. No pulsa entregar en Companion. Las cartas protegidas, cedidas, no revisadas, de otra edición, consumidas o repetidas por ID se rechazan. En el formato por puntos, el progreso procede de las entregas confirmadas, no de un contador editable.

El historial permite **restaurar** una entrega local. La app comprueba que cada carta siga perteneciendo a ese consumo y restaura toda la operación de manera atómica. En puntos, descuenta solo la aportación de esa entrega. Esta restauración no recupera una carta que ya entregaste realmente en EA.

Una vez hay entregas activas no puedes cambiar las reglas del segmento. Restaura primero lo necesario si estás corrigiendo una prueba local. Los duplicados son copias diferentes con IDs diferentes; reenviar el mismo ID nunca cuenta como otra copia.

## 6. Novedades y contenido que va cambiando

**Actualizar noticias** consulta fuentes públicas fijas de EA y muestra enlaces con fecha de consulta. No inicia sesión ni consulta tu cuenta. Si no hay red, EA rechaza la petición o cambia el HTML, se conserva la información anterior.

Para agregar o corregir conjuntos/evoluciones, importa un paquete JSON en **Novedades**. Revisa edición, fecha y contenido antes de confirmar. La confirmación exige el mismo hash del paquete revisado; repetir un paquete ya importado no vuelve a aplicar una versión antigua sobre cambios posteriores. El `slug` identifica cada definición para actualizarla.

Un titular nuevo no modifica por sí solo las reglas del solver. Los DCP nuevos se introducen y revisan en DCP. El proyecto no ofrece un inventario completo y automático del contenido de temporada. Consulta [FC27_UPGRADE.md](FC27_UPGRADE.md) para el formato de paquetes.

## Companion y lectura del inventario

Inicia Android y la sesión de Companion manualmente. En **Emulador**, conecta el dispositivo y abre **Mi club → Futbolistas**. El panel puede leer la jerarquía accesible; si no existe, recurre a OCR conservador. Ninguna captura se importa automáticamente.

Pulsa **Nueva lectura**, **Leer página actual** y, cuando corresponda, **Avanzar y leer siguiente**. La app valida dispositivo, resolución y cambio de página. Una lectura admite 50 páginas/1000 candidatos; **Continuar en un lote nuevo** conserva una referencia para evitar repetir la página límite.

Corrige los candidatos y selecciona solo los comprobados. No se aceptan nombres «Por revisar» ni valores de relleno. La importación exige `IMPORTAR <id>`, hasta 500 cartas por solicitud; archivar los nombres exactos de la demo exige `REEMPLAZAR DEMO <id>`. No se eliminan físicamente las cartas. Una sesión cerrada o una selección ya importada no puede reutilizarse para crear copias inadvertidas.

Para depuración inalámbrica de Android, el puerto de emparejamiento puede ser distinto del puerto de conexión. El código ADB de seis dígitos se utiliza una sola vez y no se persiste. La aplicación no pide códigos ni contraseñas de EA.

### Preparación asistida de un DCP tradicional

1. Conecta el dispositivo y abre el segmento correcto.
2. Captura y calibra búsqueda, texto, resultado y agregar; la calibración es una medición local, no un toque enviado.
3. Desde una solución revisada de DCP crea un plan.
4. Prepara los pasos, revísalos y autoriza con `PREPARAR <id>`.
5. Observa la ejecución y cancela si la pantalla no coincide.
6. Comprueba las cartas en el dispositivo y decide manualmente si entregar.

El plan reserva el dispositivo, vuelve a validar sus datos y comprueba identidad visual antes de seleccionar. Una pantalla inaccesible, ambigua o modificada detiene la preparación. Los planes interrumpidos por reinicio no se reanudan solos. `completed` significa preparación terminada, no entrega realizada. Un cambio de interfaz/resolución requiere recalibrar y comprobar la compatibilidad; los DCP por puntos no admiten preparación ADB en esta versión.

## Objetivos, IA, Ajustes y respaldo

Objetivos conserva progreso y recordatorios locales. El chat opcional usa Ollama y un resumen controlado del club; no ejecuta cambios. Ajustes permite corregir perfil/presupuesto y revisar capturas OCR. El tema se conserva en el navegador.

Respaldar antes de actualizar protege todo el historial, no solo el inventario exportado. Los scripts de PowerShell resuelven la configuración de Compose; la restauración exige un dump dentro de `backups`, crea una copia previa y detiene la API durante el proceso. Un CSV es útil para intercambiar jugadores, pero no reemplaza un respaldo de PostgreSQL.
