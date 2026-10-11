# Club Lab · FC 27

Asistente local y no oficial para **analizar tus jugadores, armar plantillas, planificar DCP y llevar una Galería del club**. Incluye evoluciones con caminos y cadenas simuladas, noticias públicas y paquetes de contenido revisables. React/TypeScript, FastAPI, PostgreSQL y OR-Tools; chat local opcional con Ollama y lectura asistida de Companion por ADB.

El repositorio conserva el nombre `emuladordcp26` y los nombres de sus volúmenes para que actualizar no separe tu instalación de sus datos. **FC27 es la edición inicial; los datos existentes de FC26 se conservan como archivo separado.**

**Revisión del planificador, 11 de octubre de 2026:** la entrada comprueba sesión, contexto y capacidades. La conexión EA muestra **Integración pendiente**: falta autorización/documentación para este proyecto. Solo la elección explícita de **Abrir registro local** habilita simulaciones con datos locales. Incluye planes revisables, reservas de cartas/monedas, cinco perfiles de plantilla, fichajes condicionados a datos verificados, mercado/diario y 50 referencias. [Implementación, comparación y límites](docs/FC27_PLANNER.md).

Para probar esta rama con datos desechables y sin usar los volúmenes normales: `docker compose -f docker-compose.review.yml up --build -d`, luego abre `http://localhost:8081`. La base de revisión usa memoria temporal; no guardes datos únicos en ella.

## Qué puedes hacer

| Área | Funciones implementadas |
| --- | --- |
| Club | Crear, editar, buscar y paginar cartas; importar CSV/XLSX con revisión; registrar atributos, posiciones alternativas, PlayStyles, roles, cesiones, evolución, holográficos y puntuación revisada. |
| Análisis | Ver cobertura por posición, referentes, huecos y datos pendientes. La recomendación explica qué información utilizó. |
| Plantillas | Proponer once y siete suplentes en diez formaciones; comparar cinco objetivos, fijar/excluir jugadores y usar posiciones alternativas. Guardar y proteger equipos completos. |
| Galería | Registrar adquisiciones locales, conservar cartas que ya no están disponibles, crear conjuntos con filtros/etiquetas y evaluar grados cuando hay reglas y puntos revisados. |
| Evoluciones | Registrar requisitos y caminos, simular hasta cinco evoluciones encadenadas con topes y comprobar elegibilidad sin modificar las cartas. |
| DCP | Resolver requisitos tradicionales o puntuación revisada, gestionar entregas parciales, proteger jugadores y restaurar una entrega local desde su historial. |
| Novedades | Consultar referencias públicas de EA, actualizar titulares e importar versiones revisadas de conjuntos/evoluciones sin editar código. |
| Companion | Lecturas manuales revisables, requisitos e inspección; máximo 20 formularios por bloque. Envío de pulsaciones deshabilitado por falta de permiso aplicable. |

Los datos pertenecen a tu instalación. El proyecto no inicia sesión en EA ni usa una API autenticada del club. Las confirmaciones registran decisiones/resultados locales; no ejecutan operaciones en EA. La sesión local no sustituye autenticación multiusuario.

## Empezar

Requiere Docker Engine/Desktop con Compose. Ollama y un emulador consumen memoria adicional; el stack base ya no exige GPU.

```bash
# Copia .env.example a .env si necesitas cambiar puertos o configuración.
docker compose up --build -d
```

Abre [la aplicación](http://localhost:8080), [la documentación HTTP](http://localhost:8080/api/docs) o [el health check](http://localhost:8080/health).

Una instalación nueva crea un perfil vacío. **`SEED_DEMO=false` es el valor predeterminado.** Los 132 jugadores demostrativos son ficticios y solo se cargan si se solicita la demo antes de crear el primer perfil. El seed no rellena ni reemplaza una base que ya tenga perfil. Para probar con demo, usa una instalación desechable configurada desde su primer arranque con `SEED_DEMO=true`.

### Si ya utilizabas FC26

1. Crea un respaldo de tu instalación antes de actualizar.
2. Actualiza el código y ejecuta `docker compose up --build -d`.
3. Alembic llega a `0009`: conserva FC26/FC27 y sus historiales, y guarda lo heredado en un contexto local sin vincular.
4. Cambia de edición desde la cabecera para consultar FC26. Importa tus cartas actuales con FC27 seleccionado.

No cambies los nombres de los volúmenes ni uses `docker compose down -v` para actualizar. [Guía de actualización FC27](docs/FC27_UPGRADE.md).

## Analizar tu club y armar un equipo

1. En **Club**, crea cartas o importa un CSV/XLSX. Revisa la vista previa y confirma el mismo archivo.
2. Completa posiciones alternativas y atributos si quieres comparar el encaje por puesto. Registra PlayStyles/roles solo cuando los hayas comprobado.
3. En **Análisis**, comprueba cobertura, jugadores destacados y advertencias sobre datos incompletos.
4. Pulsa **Armar un…** o entra en **Plantillas**. Elige formación y enfoque; puedes mantener jugadores concretos o excluirlos.
5. Pulsa **Proponer once y suplentes**. Revisa las explicaciones y los huecos. Solo una propuesta completa puede guardarse como equipo.
6. Protege el equipo para que sus cartas queden fuera de los DCP. Esta protección se suma a las protecciones individuales.

Formaciones: **4-3-3, 4-4-2, 4-2-3-1, 4-1-2-1-2 y 3-5-2**. El encaje es una heurística local basada en media, atributos registrados y pequeños ajustes; la química suma los valores registrados por carta. No representa una garantía de rendimiento ni la fórmula completa del juego. [Detalles del optimizador](docs/OPTIMIZER.md).

### Formato de importación

Columnas obligatorias:

```csv
name,rating,position,league,club,nationality
Ejemplo local,84,MC,Liga de ejemplo,Club de ejemplo,Colombia
```

También se admiten `game_version`, `card_id`, `base_card_id`, `card_type`, `price`, `chemistry`, `protected`, `tradable`, `special`, `duplicate_untradeable`, `alternate_positions`, `attributes`, `playstyles`, `playstyles_plus`, `roles`, `skill_moves`, `weak_foot`, `is_loan`, `is_evolution`, `is_holographic`, `gallery_score`, `data_source` y `data_reviewed`, además de los campos compatibles anteriores. Listas y objetos se escriben como JSON dentro de la celda. Exportar primero una carta completa proporciona una plantilla con todas las columnas.

La revisión queda vinculada al archivo y a la edición. Cambiar cualquiera exige otra revisión. Repetir una confirmación ya recibida no crea otra copia; importar deliberadamente un nuevo archivo no hace un upsert automático del inventario.

## Galería, evoluciones y novedades

**Galería** conserva el registro local de cartas obtenidas. Las cesiones no se registran; una evolución requiere identificar su carta base. Las cartas históricas cuentan para colecciones, pero no vuelven a estar disponibles para jugar o entregar. Al corregir la identidad de una carta, su entrada se reconcilia para evitar duplicar la colección.

Las puntuaciones deben revisarse. La referencia base incluida no calcula por sí sola todas las bonificaciones de rareza u holográficos. Sin puntos y reglas completos se muestran pendientes, no un grado supuesto. La app no acredita recompensas ni modifica la Galería de EA.

**Evoluciones** permite introducir requisitos, caminos y topes, y comparar una cadena sobre una carta registrada. Si faltan atributos necesarios para verificarla, la simulación lo indica y se detiene. No aplica mejoras al inventario ni al juego.

**Novedades** incluye referencias verificadas el 10 de octubre de 2026. Actualizar noticias consulta páginas públicas de EA; si fallan o cambian de formato, conserva la última lista. Los conjuntos y evoluciones se actualizan mediante un paquete JSON revisado. La fecha y procedencia quedan registradas. No hay un catálogo automático completo de todos los DCP, campañas, precios o evoluciones en vivo.

Fuentes de las novedades de FC27: [FUT Deep Dive de EA](https://www.ea.com/games/ea-sports-fc/fc-27/news/pitch-notes-fc27-fut-deep-dive) y [actualización del lanzamiento de EA](https://www.ea.com/es/games/ea-sports-fc/fc-27/news/pitch-notes-fc27-launch-update). El esquema de paquetes y ejemplos están en [FC27_UPGRADE.md](docs/FC27_UPGRADE.md).

## Configuración local

Variables principales en [.env.example](.env.example):

- `APP_PORT=8080`, `POSTGRES_PORT=55432`, `APP_BIND_HOST=127.0.0.1`.
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`. Deja `DATABASE_URL` vacío para derivarlo de esos valores, incluyendo contraseñas con caracteres especiales.
- `SEED_DEMO=false`, `MAX_UPLOAD_MB=10`, `CORS_ORIGINS`.
- `OLLAMA_URL`, `OLLAMA_MODEL`, `OLLAMA_KEEP_ALIVE` y límites `*_MEMORY_LIMIT`.
- `ADB_ENABLED`, `ADB_DEFAULT_ADDRESS` y `ADB_SERVER_SOCKET`, según teléfono/AVD y servidor ADB.

Nginx es la entrada web. PostgreSQL y Nginx publican sus puertos en loopback; backend, frontend y Ollama quedan en la red interna. No hay autenticación multiusuario: una exposición a otras máquinas requiere configurar acceso y protección de red. No confirmes `.env` ni respaldos en Git.

Ollama necesita descargar un modelo para el chat:

```bash
docker compose exec ollama ollama pull qwen2.5:3b
```

La ausencia de Ollama o del modelo no impide usar el club. Para NVIDIA, utiliza explícitamente el archivo adicional y un runtime de contenedores compatible:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d
```

## Android / Companion

El usuario inicia Android y su sesión de Companion. La guía de [Companion](docs/USER_GUIDE.md#companion-y-lectura-del-inventario) describe conexión, lectura, corrección de candidatos y calibración.

Los scripts Windows mantienen el nombre técnico `FC26_Companion` del AVD existente. `start-android-avd.ps1` abre el AVD y selecciona su serial; los cambios persistentes de resolución, densidad o paquetes solo se aplican con `-OptimizeDevice`. `stop-android-avd.ps1` detiene el AVD elegido sin matar el servidor ADB compartido.

Un plan tradicional exige la frase `PREPARAR <id>`, se vuelve a validar y comprueba la identidad visual antes de seleccionar cartas. Una interfaz no reconocida detiene la preparación. Los DCP por puntos se gestionan localmente y no generan un plan ADB. La compatibilidad visual debe comprobarse en la versión concreta de Companion del usuario.

## Operación y respaldo

```bash
docker compose down                    # detener, conservar datos
docker compose logs --tail=200 backend database nginx
docker compose exec backend alembic current
docker compose exec backend alembic check
```

En Windows:

```powershell
scripts/backup.ps1
scripts/export-data.ps1
scripts/restore.ps1 -BackupFile backups/archivo.dump
```

Los scripts resuelven usuario, base y puerto desde la configuración efectiva de Compose. Restaurar crea un dump previo, detiene el backend, restaura en una transacción y vuelve a iniciarlo. Prueba primero con una instalación desechable. `make reset` borra volúmenes y nunca es un paso de actualización.

## Desarrollo y pruebas

El planificador se verificó localmente con **154 Pytest en PostgreSQL, 25 Vitest y 12 recorridos Playwright**, build de producción y migraciones a `0009`, usando datos desechables. Consulta [TESTING.md](docs/TESTING.md) para resultados, reproducción y límites; la conexión con el proveedor y el club real siguen pendientes.

La [ejecución CI del 10 de octubre de 2026](https://github.com/ARVI17/emuladordcp26/actions/runs/38020243563) verificó el código `ba9c17b`: **111 pruebas backend con PostgreSQL, 24 pruebas frontend y 6 recorridos Playwright en móvil/escritorio**, además de la migración de 132 cartas FC26, TypeScript/Vite/PWA y las configuraciones Compose base/GPU. La auditoría npm de producción terminó sin avisos; el árbol de desarrollo conserva el aviso documentado en [SECURITY.md](docs/SECURITY.md).

Consulta [TESTING.md](docs/TESTING.md) para comandos, alcance de la evidencia y pruebas pendientes con el stack Docker completo, PowerShell y hardware Companion. Todos los inventarios de prueba son ficticios y desechables.

Documentación: [guía de usuario](docs/USER_GUIDE.md), [actualización FC27](docs/FC27_UPGRADE.md), [mapa técnico](docs/PROJECT_MAP.md), [arquitectura](docs/ARCHITECTURE.md), [optimizadores](docs/OPTIMIZER.md), [seguridad](docs/SECURITY.md) y [limitaciones](docs/KNOWN_LIMITATIONS.md).
