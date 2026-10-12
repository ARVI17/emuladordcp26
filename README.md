# Club Lab · FC 27

Asistente local y no oficial para **analizar tus jugadores, armar plantillas, planificar DCP y llevar una Galería del club**. Incluye evoluciones con caminos y cadenas simuladas, noticias públicas y paquetes de contenido revisables. React/TypeScript, FastAPI, PostgreSQL y OR-Tools; chat local opcional con Ollama y lectura asistida de Companion por ADB.

El repositorio conserva el nombre `emuladordcp26` y sus volúmenes. **FC27 es la única edición pública.** El histórico permanece oculto y protegido; no hay selector ni conversión automática. [Admisión, cuarentena y evidencia](docs/FC27_EXCLUSIVE.md).

**Revisión del planificador, 11 de octubre de 2026:** la entrada comprueba sesión, contexto y capacidades. La conexión EA muestra **Integración pendiente**: falta autorización/documentación para este proyecto. Solo la elección explícita de **Abrir registro local** habilita simulaciones con datos locales. Incluye planes revisables, reservas de cartas/monedas, cinco perfiles de plantilla, fichajes condicionados a datos verificados, mercado/diario y 50 referencias. [Implementación, comparación y límites](docs/FC27_PLANNER.md).

La instalación personal utiliza únicamente `emuladordcp26` en `http://localhost:8080`. Inicia los contenedores existentes con `powershell -File scripts/fc27.ps1 Inicio`; consulta `Estado` o detén con `Parada`. El script no construye, recrea ni actualiza la instalación. Las pruebas usan `python scripts/verify_docker.py --scope full` y cierran sus recursos al terminar. [Operación y pruebas](docs/DEVELOPMENT_WORKFLOW.md).

## Qué puedes hacer

| Área | Funciones implementadas |
| --- | --- |
| Club | Crear, editar, buscar y paginar cartas; importar CSV/XLSX con revisión; registrar atributos, posiciones alternativas, PlayStyles, roles, cesiones, evolución, holográficos y puntuación revisada. |
| Análisis | Ver cobertura por posición, referentes, huecos y datos pendientes. La recomendación explica qué información utilizó. |
| Plantillas | Once y siete suplentes entre once formaciones documentadas mientras su revisión esté vigente; cinco objetivos, fijados/excluidos y protecciones. |
| Galería | Registrar adquisiciones locales, conservar cartas que ya no están disponibles, crear conjuntos con filtros/etiquetas y evaluar grados cuando hay reglas y puntos revisados. |
| Evoluciones | Registrar requisitos y caminos, simular hasta cinco evoluciones encadenadas con topes y comprobar elegibilidad sin modificar las cartas. |
| DCP | Resolver requisitos tradicionales o puntuación revisada, gestionar entregas parciales, proteger jugadores y restaurar una entrega local desde su historial. |
| Novedades | Artículos FC27 fechados, descubrimiento de enlaces pendientes y paquetes de reglas conservados como borradores hasta acreditar su contenido. |
| Companion | Lecturas manuales revisables, requisitos e inspección; máximo 20 formularios por bloque. Envío de pulsaciones deshabilitado por falta de permiso aplicable. |

Los datos pertenecen a tu instalación. El proyecto no inicia sesión en EA ni usa una API autenticada del club. Las confirmaciones registran decisiones/resultados locales; no ejecutan operaciones en EA. La sesión local no sustituye autenticación multiusuario.

## Empezar

Requiere Docker Engine/Desktop con Compose. Ollama y un emulador consumen memoria adicional; el stack base ya no exige GPU.

```bash
# Instalación existente, desde cualquier carpeta/worktree:
powershell -ExecutionPolicy Bypass -File scripts/fc27.ps1 Inicio
```

Abre [la aplicación](http://localhost:8080), [la documentación HTTP](http://localhost:8080/api/docs) o [el health check](http://localhost:8080/health).

Una instalación nueva crea un perfil vacío y referencias documentales, sin cartas propias. El arranque normal no carga demo, incluso si conserva una variable `SEED_DEMO` heredada. Los fixtures sintéticos pertenecen exclusivamente al entorno de pruebas desechable.

### Si ya utilizabas FC26

1. Crea un respaldo de tu instalación antes de actualizar.
2. Prepara imágenes identificadas por commit, restaura el respaldo en un entorno aislado y revisa el procedimiento de actualización antes de aplicarlo al principal.
3. Alembic llega a `0014`: conserva cartas, saldos y reglas históricas. Las copias y definiciones sin evidencia vigente quedan fuera de las funciones activas, sin borrarse.
4. Abre el registro manual FC27. Revisa las declaraciones en cuarentena contra el catálogo exacto; una marca manual no certifica una variante ni recupera saldos históricos.

No cambies los nombres de los volúmenes ni uses `docker compose down -v` para actualizar. [Guía de actualización FC27](docs/FC27_UPGRADE.md).

## Analizar tu club y armar un equipo

1. En **Club**, crea cartas o importa un CSV/XLSX. Revisa la vista previa y confirma el mismo archivo.
2. Completa posiciones alternativas y atributos si quieres comparar el encaje por puesto. Registra PlayStyles/roles solo cuando los hayas comprobado.
3. En **Análisis**, comprueba cobertura, jugadores destacados y advertencias sobre datos incompletos.
4. Pulsa **Armar un…** o entra en **Plantillas**. Elige formación y enfoque; puedes mantener jugadores concretos o excluirlos.
5. Pulsa **Proponer once y suplentes**. Revisa las explicaciones y los huecos. Solo una propuesta completa puede guardarse como equipo.
6. Protege el equipo para que sus cartas queden fuera de los DCP. Esta protección se suma a las protecciones individuales.

Las formaciones disponibles proceden del catálogo documentado FC27. 4-3-3 y 4-3-3 Holding son opciones distintas. El encaje es una heurística local; la química oficial permanece sin verificar. [Detalles del optimizador](docs/OPTIMIZER.md).

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

Las puntuaciones deben comprobarse en el juego. La tabla base no acreditada se retiró. Sin puntos y reglas completos se muestra estado pendiente; la app no acredita recompensas ni modifica la Galería de EA.

**Evoluciones** permite introducir requisitos, caminos y topes, y comparar una cadena sobre una carta registrada. Si faltan atributos necesarios para verificarla, la simulación lo indica y se detiene. No aplica mejoras al inventario ni al juego.

**Novedades** muestra artículos con edición, publicación y revisión vigentes. Los enlaces descubiertos sin esos datos quedan pendientes. Los paquetes importados conservan borradores y no acreditan reglas automáticamente. No hay catálogo completo de desafíos, precios o evoluciones en vivo.

Fuentes incorporadas: [FUT Deep Dive de EA](https://www.ea.com/games/ea-sports-fc/fc-27/news/pitch-notes-fc27-fut-deep-dive) y [actualización de lanzamiento de EA](https://www.ea.com/games/ea-sports-fc/fc-27/news/fc-27-fut-developer-launch-update). El esquema de paquetes está en [FC27_UPGRADE.md](docs/FC27_UPGRADE.md).

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

El planificador se verifica mediante `python scripts/verify_docker.py --scope full`: PostgreSQL aislado, build, Pytest, Vitest y Playwright móvil/escritorio sobre Nginx. Consulta el registro de cada sprint en [TESTING.md](docs/TESTING.md) para conteos y límites; la conexión con el proveedor y el club real siguen pendientes. [Práctica y diario](docs/PRACTICE.md) y [mercado/agenda A-B](docs/MARKET_AGENDA.md) describen las ampliaciones recientes.

La [ejecución CI del 10 de octubre de 2026](https://github.com/ARVI17/emuladordcp26/actions/runs/38020243563) verificó el código `ba9c17b`: **111 pruebas backend con PostgreSQL, 24 pruebas frontend y 6 recorridos Playwright en móvil/escritorio**, además de la migración de 132 cartas FC26, TypeScript/Vite/PWA y las configuraciones Compose base/GPU. La auditoría npm de producción terminó sin avisos; el árbol de desarrollo conserva el aviso documentado en [SECURITY.md](docs/SECURITY.md).

Consulta [TESTING.md](docs/TESTING.md) para comandos, alcance de la evidencia y pruebas pendientes con el stack Docker completo, PowerShell y hardware Companion. Todos los inventarios de prueba son ficticios y desechables.

Documentación: [guía de usuario](docs/USER_GUIDE.md), [actualización FC27](docs/FC27_UPGRADE.md), [mapa técnico](docs/PROJECT_MAP.md), [arquitectura](docs/ARCHITECTURE.md), [optimizadores](docs/OPTIMIZER.md), [seguridad](docs/SECURITY.md) y [limitaciones](docs/KNOWN_LIMITATIONS.md).
