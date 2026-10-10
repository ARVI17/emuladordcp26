# Arquitectura

Esta referencia describe la actualización local para FC 27. Los contratos detallados están en [PROJECT_MAP.md](PROJECT_MAP.md), la selección de cartas en [OPTIMIZER.md](OPTIMIZER.md) y las verificaciones pendientes en [TESTING.md](TESTING.md).

## Servicios y acceso

El navegador entra por Nginx en el puerto configurable `APP_PORT`. El proxy dirige `/` al frontend estático y `/api/*` a FastAPI. Las rutas Python no incluyen el prefijo `/api`: FastAPI usa `root_path="/api"` y TestClient llama, por ejemplo, a `/players`. El backend accede a PostgreSQL, consulta Ollama y, si el usuario lo conecta, controla un dispositivo Android mediante ADB.

| Componente | Responsabilidad | Fuente |
| --- | --- | --- |
| React, Vite y TanStack Query | Inventario, análisis, Galería, DCP, contenido, evoluciones y Companion | [frontend/src](../frontend/src) |
| Nginx de entrada | Proxy de aplicación y API, límites y cabeceras | [nginx.conf](../nginx/nginx.conf) |
| FastAPI | Validación HTTP, simulaciones y transacciones explícitas | [main.py](../backend/app/main.py), [api](../backend/app/api) |
| PostgreSQL 16 | Datos locales, historial, snapshots y configuración | [entities.py](../backend/app/models/entities.py) |
| OR-Tools CP-SAT | Selección DCP, asignación de puestos y conjuntos de Galería | [sbc.py](../backend/app/optimizers/sbc.py), [squad_analysis.py](../backend/app/services/squad_analysis.py), [gallery.py](../backend/app/services/gallery.py) |
| Ollama | Chat opcional de solo consulta sobre un resumen limitado del club | [ollama.py](../backend/app/services/ollama.py) |
| ADB, OpenCV y Tesseract | Captura, lectura revisable y preparación asistida en un dispositivo del usuario | [adb.py](../backend/app/services/adb.py), [import_export.py](../backend/app/services/import_export.py) |

[Docker Compose](../docker-compose.yml) conserva el proyecto, la red y los volúmenes `emuladordcp26` para no desconectar una instalación existente de sus datos. Los puertos publicados se vinculan por defecto a `127.0.0.1` mediante `APP_BIND_HOST`. Los nombres heredados de base y usuario PostgreSQL tampoco convierten las cartas en una edición distinta.

El Compose base permite ejecutar Ollama sin GPU. La reserva NVIDIA se activa con [docker-compose.gpu.yml](../docker-compose.gpu.yml). El modelo se descarga por separado y persiste en su volumen; la API conserva inventario, análisis, DCP y demás funciones cuando Ollama no responde. Los límites de memoria y el pool de SQLAlchemy son configurables. El estado CPU/GPU del host no se infiere de esos archivos: debe comprobarse en una instalación real.

## Organización del backend

| Archivo o módulo | Función |
| --- | --- |
| [api/routes.py](../backend/app/api/routes.py) | Inventario, importación, plantillas, DCP, entregas/restauraciones, objetivos, perfil y chat |
| [api/analysis.py](../backend/app/api/analysis.py) | Formaciones, análisis del club y contrato de recomendación |
| [api/fc27.py](../backend/app/api/fc27.py) | Historial y conjuntos de Galería, evoluciones y contenido revisable |
| [api/emulator.py](../backend/app/api/emulator.py) | Dispositivos, lecturas, revisión e importación de candidatos y ciclo de planes ADB |
| [schemas/api.py](../backend/app/schemas/api.py) | Entradas generales, metadatos de carta y validaciones cruzadas |
| [schemas/requirements.py](../backend/app/schemas/requirements.py) | Requisitos DCP tradicionales y por puntos, compartidos entre selección y confirmación |
| [schemas/fc27.py](../backend/app/schemas/fc27.py) | Reglas de conjuntos, etiquetas, evoluciones y paquetes de contenido |
| [services/editions.py](../backend/app/services/editions.py) | Edición activa e inicialización mínima de perfil y clave de importación |
| [services/locks.py](../backend/app/services/locks.py) | Exclusión cooperativa de inventario, dispositivos, lecturas y planes |
| [services/squad_analysis.py](../backend/app/services/squad_analysis.py) | Protección efectiva, identidad de jugadores, posiciones y encaje local |
| [services/gallery.py](../backend/app/services/gallery.py) | Historial local por versión de carta, conciliación y evaluación de conjuntos |
| [services/evolutions.py](../backend/app/services/evolutions.py) | Proyección conservadora de ramas y cadenas de evoluciones |
| [services/content.py](../backend/app/services/content.py) | Referencias incluidas y lectura acotada de noticias públicas de EA |

## Ediciones y persistencia

`Profile.game_version` determina la edición activa. Jugadores, plantillas, desafíos, objetivos, entregas, lecturas y definiciones nuevas conservan su edición; los segmentos pertenecen a la de su desafío. Cambiar de edición selecciona otro inventario lógico: no transforma ni traslada cartas.

La [migración 0005](../backend/alembic/versions/0005_fc27_club.py) conserva los datos anteriores como FC26, incorpora los campos y entidades nuevos y establece FC27 como edición inicial del perfil actualizado. Las vistas vacías de FC27 tras migrar no significan que se haya borrado el archivo FC26.

`Player` representa una copia del inventario. Guarda posiciones alternativas, atributos, PlayStyles, roles, identificadores de carta/base, cesión, evolución, holografía, procedencia, revisión y puntuación registrada. `deleted` mantiene el archivo lógico; `consumed_by_submission_id` identifica la entrega que la consumió. `Submission` conserva requisitos y cartas en un snapshot, valor monetario y contribución de puntos.

`GalleryEntry` mantiene una versión de carta en el historial local, incluso cuando deja de estar disponible. Su identidad es única dentro de cada edición y puede reconciliarse cuando se corrige un identificador. `GallerySet` almacena reglas, etiquetas y umbrales revisados; `EvolutionDefinition` contiene requisitos y caminos de mejora. Registrar o editar datos locales no modifica la Galería ni activa una evolución en EA.

El historial de chat nuevo incluye edición en sus metadatos; los mensajes antiguos sin ella se consultan como FC26. Auditoría y configuración siguen siendo registros locales comunes. Los ajustes privados que empiezan por `_`, incluidos secretos y recibos de importación, quedan fuera de la API pública de ajustes.

## Lecturas, simulaciones y transacciones

Las recomendaciones, optimizaciones y vistas previas de evoluciones calculan resultados sin consumir ni modificar cartas. Guardar una plantilla o confirmar un DCP son operaciones diferentes.

La protección efectiva es la unión de `Player.protected` y la pertenencia a cualquier plantilla protegida. Cambiar la protección de una plantilla no sobrescribe la decisión manual de otra carta. Las cartas protegidas pueden jugar en las recomendaciones, pero no se consumen al confirmar un DCP.

Las mutaciones de inventario comparten la reserva `inventory`. Después de obtenerla se releen datos, se valida el estado actual y se confirma una unidad lógica con su auditoría. PostgreSQL usa bloqueos asesores de sesión en una conexión independiente del pool ORM, conservados durante el commit. La contención entre procesos produce un 409 para reintentar; SQLite utiliza bloqueos dentro del proceso y no demuestra por sí sola el comportamiento PostgreSQL.

Confirmar revalida la solución, guarda el snapshot y marca cada copia como consumida por esa entrega. Restaurar verifica todos los propietarios antes de modificar datos. El progreso de un DCP por puntos se calcula desde sus entregas activas; restaurar revierte solo la contribución correspondiente. Una restauración local nunca recupera una carta ya entregada en el juego.

## Importación y contenido revisable

CSV/XLSX y OCR se procesan en memoria con límites. El trabajo de importación y OCR se ejecuta fuera del bucle asíncrono de FastAPI. La importación de jugadores valida cada fila y exige una vista previa: un token firmado vincula archivo, formato y edición durante una hora. Un recibo persistido evita duplicar una confirmación repetida.

El contenido incluido reside en [fc27_content.json](../backend/app/data/fc27_content.json), con fuentes y fechas. `POST /content/refresh` consulta únicamente fuentes públicas predefinidas para noticias; conserva el último contenido disponible si falla. No descarga el inventario de una cuenta ni traduce noticias automáticamente a requisitos ejecutables.

Los paquetes JSON de conjuntos/evoluciones siguen un flujo de vista previa, hash del contenido y confirmación. Actualizan definiciones por identificador y edición, con recibos de repetición. Las reglas requieren revisión humana; disponer de una URL de fuente no certifica los valores introducidos.

## ADB y datos temporales

El backend aporta un cliente ADB y controles asistidos; el usuario inicia su teléfono o emulador. Una lectura de inventario queda ligada a dispositivo, resolución y edición. Acumula candidatos con identificadores estables, firmas de página, hasta 50 páginas/1000 candidatos y confirmación explícita de las filas revisadas. Los bytes de captura y la jerarquía temporal no forman parte del inventario persistido.

Los planes tradicionales verifican de nuevo requisitos, disponibilidad, protección, identidad y pantalla antes de prepararse y ejecutarse. Las reservas por dispositivo impiden intercalar operaciones cooperativas sobre una misma pantalla. La generación de ejecución y el estado del trabajador distinguen tareas vigentes de cancelaciones o intentos anteriores.

Los DCP por puntos quedan excluidos de la preparación ADB actual. Un plan `completed` significa que terminaron sus pasos de preparación; la pulsación final de entrega no forma parte del plan. La compatibilidad visual con Companion FC27 requiere todavía validación con hardware y datos desechables.

## Inicialización

[entrypoint.sh](../backend/entrypoint.sh) aplica las migraciones, ejecuta [bootstrap.py](../backend/app/db/bootstrap.py) y arranca Uvicorn. El bootstrap crea el perfil mínimo y la clave de importación incluso con `SEED_DEMO=false`, valor predeterminado.

La demo es opcional, idempotente y usa cartas ficticias marcadas `data_source="demo"`. No demuestra disponibilidad de jugadores, campañas ni DCP reales. Cuando se ejecuta un comando explícito, como pytest, el entrypoint lo invoca directamente; la suite administra su propia base de pruebas.
