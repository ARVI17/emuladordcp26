# Limitaciones conocidas

Estado del 11 de octubre de 2026. [FC27_PLANNER.md](FC27_PLANNER.md) distingue cada módulo de la integración pendiente. [TESTING.md](TESTING.md) separa resultados actuales e históricos.

## Club real y contexto

No hay acceso EA autorizado para esta aplicación. Faltan aprobación, protocolo, permisos, identidad/copia, cobertura/paginación, cuotas y frescura documentadas. La sesión local y una importación revisada no verifican una cuenta. Al entrar se muestra **Integración pendiente**; las simulaciones locales requieren elegirlas expresamente. No se realizaron pruebas contra cuenta/proveedor/hardware reales.

El reconciliador es un contrato interno probado con fixtures, sin adaptador ni cargador público de instantáneas verificadas. Una futura integración debe demostrar sus garantías antes de utilizarlo. La frescura máxima de 15 minutos es un límite del producto; no una promesa de actualización de EA. Las migraciones y fixtures usan sesiones internas sin los filtros HTTP: no deben exponerse al cliente.

Los contextos aíslan registros personales en una instalación de un propietario. No hay autenticación multiusuario. Publicar requiere TLS, autenticación y control de red. No se copiaron datos originales al stack desechable de revisión.

## Análisis, planes y mercado

El encaje es una heurística, no una medida de victorias. Compara diez formaciones y cinco objetivos, agrupando coincidencias. Banquillo y asignación disjunta son heurísticos posteriores/secuenciales. No modela animaciones, técnico, habilidad, fatiga ni toda la táctica del juego. Homónimos se separan con ID de futbolista fiable; sin él la agrupación sigue siendo aproximada.

Química oficial desconocida y media local aproximada. La suma histórica por carta permanece por compatibilidad, etiquetada. Ninguna solución garantiza aceptación oficial. Los requisitos tradicionales conservan los límites expresables en el esquema, incluyendo posiciones principales.

El cálculo conjunto está acotado a 24 copias/6 segmentos, 20 000 combinaciones y cinco segundos. Declara timeout/factibilidad y solo llama óptimo al espacio examinado completamente. No prueba el óptimo del club fuera de la selección. Las entregas parciales necesitan aceptación específica; los sobrantes consumidos no se recuperan. Restaurar exige origen explícito de simulación local.

Los planes reservan recursos locales; no ejecutan operaciones EA. Un gasto confirmado queda comprometido hasta conciliar monedas posteriores. El presupuesto local no acredita saldo. Datos desconocidos, ausencias, anuncios, resultados inciertos y compras propuestas no se convierten en recursos disponibles. Retirar el candado manual no elimina otras protecciones acumuladas.

No hay feed autorizado de precios/ventas. Las cotizaciones manuales exigen variante, edición, mercado, tipo, fuente y tiempo, pero no prueban que el anuncio siga disponible. Fichajes requiere inventario/monedas verificados y muestra química/costes complementarios pendientes. Los tramos son porcentajes del presupuesto, no categorías universales. Volumen desconocido. El diario usa hasta 500 registros recientes; nunca volumen global. Tasa del 5 % y redondeo son hipótesis.

## Galería, evoluciones y referencias

Galería conserva adquisiciones locales aunque dejen de estar disponibles; no reclama recompensas. Puntos, reglas y progreso oficial requieren evidencia. La carta base Evo puede seguir pendiente. Simular una cadena no activa caminos ni modifica atributos reales. Coste máximo y plazos se registran tras revisión, sin descargar automáticamente tareas o efectos sobre transferibilidad.

Las 50 referencias conservan el alcance aportado por el usuario. Se contrastaron fuentes clave de reglas, permisos y formaciones; no se afirma haber revalidado las 50 páginas individualmente. R20–R22 solo acreditan metadatos audiovisuales. Una URL no acredita vigencia ni licencia de extracción. Las revisiones guardan diferencias/versiones anteriores sin modificar reglas o planes por sí solas. El mantenimiento programable es un recordatorio, no un rastreador. Las noticias EA son una consulta manual acotada que puede fallar conservando lo anterior.

## Importación y Companion

El mismo contenido CSV/XLSX en contexto/edición iguales es idempotente aunque cambie la vista previa. Otro contenido no dispone de IDs externos de copia: no es sincronización. Nombre/media/posición detecta ambigüedad y evita resucitar consumidas, pero no identifica dos copias EA idénticas.

OCR siempre requiere revisión. Resúmenes sin candidatos y detalles de hasta 20. Observar Companion hace una lectura manual de jerarquía, sin temporizador/captura/OCR/toque. Pulsaciones y ejecución ADB están deshabilitadas por falta de permiso aplicable; se conserva el motor histórico y sus pruebas ficticias.

## Verificación pendiente

Faltan proveedor/club real, Android, Safari, GPU/Ollama en esta rama y prueba de los scripts PowerShell de backup/restore sobre una instalación real. Sí se construyó/inició el stack aislado con Nginx, se probaron degradaciones sin Ollama/ADB, migraciones PostgreSQL y dump/restauración con datos desechables. Ninguna sustituye las pendientes.
