# Limitaciones conocidas

Estado de la actualización local FC27, revisado el **10 de octubre de 2026 UTC**. El alcance implementado y las pruebas ejecutadas están en [ARCHITECTURE.md](ARCHITECTURE.md), [OPTIMIZER.md](OPTIMIZER.md) y [TESTING.md](TESTING.md).

## Cuenta, ediciones y datos

La aplicación administra un registro local de un solo usuario. No utiliza una API autenticada de EA ni conoce automáticamente el club completo, el inventario vendido o el historial anterior al registro. Una importación revisada o una captura ADB puede seguir conteniendo errores humanos.

Los datos migrados se conservan como FC26 y el perfil inicia FC27. Cambiar la edición no convierte cartas ni lleva su historial al juego nuevo. El patrón de versión permite preparar datos de otras ediciones, pero admitir una etiqueta futura no certifica compatibilidad con sus reglas o pantallas. Las fuentes públicas configuradas y los datos incluidos son los que muestra [content.py](../backend/app/services/content.py).

No hay precios de mercado en tiempo real. Precio, atributos, posiciones alternativas, identificadores, roles y puntuaciones son valores registrados o revisados por el usuario. Los ejemplos y la demo son ficticios; no se deben presentar como plantillas o campañas reales.

Sin identificadores fiables, versiones y homónimos pueden confundirse. El analizador agrupa también nombres normalizados para evitar alinear dos versiones de la misma persona, lo que puede excluir homónimos válidos. Corregir una identidad ayuda a la conciliación de Galería, pero no valida el dato contra EA.

## Análisis y DCP

El encaje, la media y la química son cálculos locales. Las cinco formaciones disponibles, los pesos de atributos y los ajustes por roles/PlayStyles no modelan todos los efectos de táctica, animaciones, técnico, forma de jugar o actualizaciones de gameplay. El banquillo se construye con una heurística posterior al once y la formación sugerida prioriza cobertura. Consulte los coeficientes y tiempos en [OPTIMIZER.md](OPTIMIZER.md).

Los solvers tienen límites de tiempo. Una solución factible puede no ser óptima; una respuesta sin solución puede reflejar el tiempo disponible además de restricciones imposibles. La prueba automatizada valida las reglas locales, no la aceptación por una interfaz concreta del juego.

Los DCP por puntos usan puntuaciones positivas explícitas y revisadas. La tabla base enlazada en contenido sirve de referencia y no completa por sí sola bonificaciones de tipos de carta, holografía o cambios posteriores. Si faltan datos, no se consume suponiendo una puntuación.

Un segmento tradicional sigue usando los requisitos tradicionales registrados, incluidas las posiciones principales. No adapta silenciosamente un DCP antiguo a un formato score. Las condiciones que la interfaz no modele deben verificarse antes de una entrega real.

Confirmar y restaurar solo cambian la base local. **Restaurar una entrega local no devuelve cartas entregadas en EA.** Los consumos heredados con más de un posible propietario se rechazan para revisión. Tampoco se puede asegurar coherencia si se modifica directamente la base saltándose validaciones y bloqueos de la API.

## Galería, contenido cambiante y evoluciones

Galería es un historial local. Registrar inventario, completar un conjunto local o mostrar una nota no reclama recompensas ni modifica la Galería de EA. Las copias de una versión comparten una puntuación revisada; si el identificador o el valor introducido es incorrecto, la consistencia interna no corrige esa información.

Una evolución sin carta base identificable queda pendiente en el historial. Las notas de conjuntos dependen de reglas, etiquetas, umbrales y puntos revisados; una URL de fuente no equivale a validación automática.

`POST /content/refresh` busca enlaces públicos en fuentes predefinidas. Puede fallar por cambios de HTML, bloqueo, red o ausencia de enlaces legibles. Conserva lo disponible e informa del error. No constituye una sincronización completa de campañas, DCP, conjuntos y evoluciones activos.

Los paquetes de contenido requieren vista previa y confirmación. Su hash detecta cambios o repetición, pero no certifica autoría ni exactitud. Actualizan definiciones por identificador: hay que revisar qué reemplazan y su edición.

La vista previa de evoluciones aplica únicamente las condiciones y mejoras expresables en [schemas/fc27.py](../backend/app/schemas/fc27.py). No activa caminos, no comprueba todas las condiciones posibles del juego y no rellena atributos desconocidos. Costes, tareas, elegibilidad adicional y cambios de plazos deben contrastarse antes de actuar.

## Importación, OCR y ADB

CSV/XLSX valida filas, rangos, booleanos y metadatos; la confirmación está vinculada a un archivo revisado y es idempotente por token. Confirmar deliberadamente nuevas vistas previas del mismo archivo permite crear nuevas copias: no hay conciliación universal de inventario externo.

OCR depende de calidad, idioma, recorte y diseño. La lectura visual puede asociar mal datos o no encontrar atributos y puntuaciones. Los límites de bytes, píxeles, tiempo y simultaneidad acotan trabajo, pero no garantizan precisión.

El proyecto aporta cliente y controles ADB. El usuario inicia y conecta su dispositivo o emulador. Las coordenadas absolutas requieren recalibración tras cambios de resolución, escala, orientación o interfaz.

Los planes tradicionales rechazan ambigüedad conocida y cambios en el snapshot. Aun así, la preparación busca por nombre y no demuestra mediante reconocimiento completo que cada resultado seleccionado sea la copia prevista. La integración visual con Companion FC27 sigue pendiente de una prueba con hardware.

Los DCP score quedan excluidos de la preparación ADB. Un estado de plan `completed` significa que terminaron los pasos de preparación, nunca que se pulsó la entrega. La cancelación evita pasos posteriores cuando el trabajador la observa; no deshace una pulsación ya enviada.

## Despliegue y verificaciones pendientes

El alcance sigue siendo local y sin autenticación multiusuario. Los puertos se publican por defecto en loopback. Exponer la instalación fuera de ese entorno exige revisar autenticación, TLS y acceso de red; las pruebas funcionales no convierten el servicio en una aplicación multiusuario.

Ollama necesita descargar un modelo y puede funcionar con CPU o con la configuración GPU opcional. La degradación sin Ollama está cubierta; el consumo real de recursos, la aceleración GPU y un arranque completo del stack dependen del host.

La [CI del 10 de octubre de 2026](https://github.com/ARVI17/emuladordcp26/actions/runs/38020243563), sobre el código [ba9c17b47c67ab4a9dadedd1de87d647db20496e](https://github.com/ARVI17/emuladordcp26/commit/ba9c17b47c67ab4a9dadedd1de87d647db20496e), pasó **111 pruebas backend en PostgreSQL 16**, incluidos los dos casos de bloqueo entre procesos. También verificó la migración desde PR1 conservando 132 cartas FC26, `alembic check` y las configuraciones Compose base/GPU. La ejecución local anterior de 109 correctos y dos omitidos correspondía a SQLite; ambos resultados quedan diferenciados en [TESTING.md](TESTING.md).

El [job frontend](https://github.com/ARVI17/emuladordcp26/actions/runs/38020243563/job/114119430117) pasó **24 Vitest en 10 archivos**, TypeScript/Vite/PWA, auditoría de producción con cero vulnerabilidades reportadas y **6/6 recorridos Playwright Chromium**. El viewport móvil fue de **390 × 664 px CSS**, con pantalla emulada de 390 × 844 px y DPR 3; el de escritorio, 1280 × 900 px. Los recorridos utilizaron Vite y una API real con datos desechables; no atravesaron el stack Docker/Nginx. El pase no certifica Safari ni dispositivos reales. El árbol de dependencias de desarrollo mantiene el alcance documentado en [SECURITY.md](SECURITY.md).

Las cuatro capturas de plantillas y Galería en móvil/escritorio de [fc27-browser-verification](https://github.com/ARVI17/emuladordcp26/actions/runs/38020243563/artifacts/11657254992) fueron revisadas sin desbordamiento horizontal ni defectos materiales observados en esas vistas. Esa revisión no cubre el resto de pantallas ni el hardware. Se registraron además 26 comprobaciones HTTP locales correctas con 223 cartas ficticias. Ninguno de esos datos proviene de un club EA real.

Continúan pendientes el build y arranque del stack Docker completo, las pruebas a través de su Nginx, backup/restauración reales con PowerShell, Safari y Companion con hardware ADB y un club EA real. Validar `docker compose config` no sustituye construir las imágenes ni arrancar sus servicios. La configuración de GPU tampoco demuestra aceleración efectiva en el host.
