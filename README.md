# emuladordcp26 — Asistente local FC 26

Aplicación local, mobile-first y no oficial para administrar el inventario revisado por el usuario, proteger cartas, organizar plantillas y objetivos, leer capturas con OCR y resolver DCP mediante optimización determinista. Puede acumular lecturas visuales del club mostrado en Companion, proponer requisitos de un DCP y preparar en un teléfono o emulador Android conectado por ADB una combinación ya calculada, siempre con autorización explícita y deteniéndose antes de la entrega final.

No inicia sesión ni se conecta directamente a las API de EA. Nunca solicita correo, contraseña, cookies, tokens ni códigos de verificación. La sesión, si se usa la preparación asistida, permanece dentro del dispositivo controlado por su propietario.

## Requisitos

- Windows 10/11, macOS o Linux con Docker Desktop/Engine y Docker Compose.
- 4 GB de RAM libres para la aplicación base; 8 GB recomendados.
- 12 GB o más de RAM si se usa Ollama junto con un emulador Android. El modelo `qwen2.5:3b` necesita además varios GB de disco.
- Puertos libres: `8080` para la aplicación y `55432` para PostgreSQL. Ambos se pueden cambiar en `.env`.

En Windows, instala Docker Desktop, activa WSL 2 cuando el instalador lo solicite y espera a que Docker indique que el motor está listo.

En equipos de 16 GB que ejecuten también un emulador Android, un límite global de WSL2 de 5 GB y 2 GB de swap ofrece un equilibrio razonable. Se configura desde WSL Settings o `%USERPROFILE%\.wslconfig`; después es necesario reiniciar Docker Desktop. No uses un límite menor sin probar OCR, compilación e inferencia.

## Inicio en un comando

```bash
docker compose up --build
```

Abre:

- Aplicación: http://localhost:8080
- Documentación de API: http://localhost:8080/api/docs
- Health check: http://localhost:8080/health

El proyecto usa contenedores dedicados llamados `emuladordcp26-database`, `emuladordcp26-backend`, `emuladordcp26-frontend` y `emuladordcp26-nginx`. No reutiliza los contenedores de otros proyectos. La base queda en el volumen `emuladordcp26_postgres_data`.

En el primer inicio, PostgreSQL se prepara, Alembic aplica las migraciones y el backend carga datos demostrativos solo si la base está vacía: 132 jugadores, 5 DCP, 10 objetivos/evoluciones y una plantilla principal.

## Configuración

Opcionalmente copia `.env.example` a `.env` y modifica los valores locales. No confirmes `.env` en Git. Las variables principales son `APP_PORT`, `POSTGRES_PORT`, `POSTGRES_PASSWORD`, `OLLAMA_MODEL`, `OLLAMA_URL`, `ADB_ENABLED`, `ADB_DEFAULT_ADDRESS`, `MAX_UPLOAD_MB` y `CORS_ORIGINS`. Los topes `BACKEND_MEMORY_LIMIT`, `DATABASE_MEMORY_LIMIT`, `FRONTEND_MEMORY_LIMIT`, `NGINX_MEMORY_LIMIT` y `OLLAMA_MEMORY_LIMIT` permiten ajustar RAM sin editar Compose. PostgreSQL usa un perfil local de 64 MB de buffers, 30 conexiones máximas y un pool SQLAlchemy de 3+2 conexiones para evitar reservas innecesarias.

Las lecturas del club no usan Ollama ni una API con créditos. **Actualizar desde Companion** realiza una sola inspección de la pantalla `Futb. de Mi Club` cuando el usuario pulsa el botón; no existe un temporizador de sincronización. **Actualizar revisión** vuelve a consultar únicamente los datos locales. La revisión detallada conserva solo 20 formularios, mientras **Cargar todo el club sin duplicados** procesa en el servidor todos los lotes pendientes bajo la frase `IMPORTAR TODO EL CLUB`. Compara nombre+media+posición con cartas activas, usadas y otros lotes para no duplicarlas.

## Comandos

```bash
make up                 # construir e iniciar en segundo plano
make down               # detener sin borrar datos
make restart            # reiniciar servicios
make logs               # seguir registros
make test               # Pytest y Vitest en contenedores temporales
make seed               # cargar demo si la base está vacía
make reset              # borrar volumen y regenerar la demo (destructivo)
make backup             # crear dump, CSV y JSON en ./backups
make restore FILE=backups/fc26-fecha.dump
```

En Windows sin `make`, usa directamente `docker compose up --build -d`, `docker compose down`, `docker compose logs -f`, `scripts/backup.ps1` y `scripts/restore.ps1 -BackupFile backups/archivo.dump`.

## Servicios Docker

- `database`: PostgreSQL 16 con volumen persistente y health check.
- `backend`: Python 3.12, FastAPI, Alembic, SQLAlchemy, OR-Tools, OpenCV, Pillow y Tesseract.
- `frontend`: React, TypeScript, Vite, Tailwind, TanStack Query, React Hook Form, Zod y PWA.
- `nginx`: único acceso público, proxy `/api`, límites de carga y cabeceras de seguridad.
- `ollama`: IA local en su propio contenedor y volumen; la aplicación sigue funcionando si temporalmente no responde.

## Emulador o teléfono Android por ADB

El backend incluye el cliente ADB dentro de su propio contenedor. Para el AVD local, Docker reutiliza el servidor ADB restringido a Windows mediante `ADB_SERVER_SOCKET=tcp:host.docker.internal:5037`; para un teléfono se conserva la conexión ADB por IP y puerto. No instales credenciales en el proyecto ni las escribas en sus formularios.

### AVD local recomendado en Windows

Para no depender de otro celular, usa el AVD `FC26_Companion` creado con las herramientas oficiales de Android. Tiene Android 15/API 35, Google Play, aceleración WHPX, marco Pixel 5 y límites de 1,5 GB de RAM y 2 núcleos. Android Studio no necesita permanecer abierto. Inícialo y selecciónalo en la aplicación con:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-android-avd.ps1
```

El script deja ADB restringido al equipo local, abre el emulador visible, espera a que Android termine y selecciona su serial en el backend. En el primer uso abre Play Store, inicia sesión manualmente, instala la aplicación oficial **EA SPORTS FC Companion** y entra tú mismo en tu cuenta EA. El proyecto no recibe ni almacena esas credenciales.

Al terminar una sesión de DCP, libera la RAM del AVD sin apagar Docker:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop-android-avd.ps1
```

El Android oficial no se ejecuta dentro de Docker Desktop en Windows porque Google no admite KVM acelerado en esa combinación. Forzarlo con virtualización anidada aumenta complejidad y consumo; las imágenes preconstruidas con Play Store también son antiguas. Por eso la API, base de datos, web, OCR y Ollama permanecen en Docker, mientras solo el runtime gráfico de Android usa WHPX en Windows. Android Studio no necesita estar abierto durante el uso.

1. Inicia el emulador y activa su acceso ADB local/TCP.
2. En **Emulador**, pulsa **Conectar** y comprueba que el dispositivo figure como disponible.
3. Abre manualmente **Mi club → Futbolistas**. En **Sincronizar mi club real**, inicia una lectura y pulsa **Actualizar desde Companion**. Cambia de página manualmente y vuelve a pulsar, o usa **Avanzar y leer siguiente** para la navegación validada. Al terminar, revisa el resumen global y escribe `IMPORTAR TODO EL CLUB` para cargar todos los lotes únicos sin crear miles de controles en el navegador.
4. Revisa nombre, media y posición, y completa liga, club, nacionalidad y demás datos que Companion no expone como texto. La lista solicita y conserva solo 20 cartas por página para reducir RAM y tráfico. Escribe `IMPORTAR <id>`; si además quieres archivar solo las 132 cartas demo, marca esa opción y escribe `REEMPLAZAR DEMO <id>`.
5. Abre el segmento DCP y pulsa **Leer requisitos DCP**. Revisa el borrador OCR antes de crearlo y optimizarlo.
6. Toma una captura y calibra por clic las zonas de búsqueda, campo, primer resultado y agregar; esos clics de calibración no se envían al dispositivo.
7. Desde una solución DCP, pulsa **Preparar en emulador**. Revisa el plan y escribe `PREPARAR <id>` para autorizar sus pulsaciones.
8. Comprueba visualmente los once jugadores. La entrega final queda deliberadamente pendiente para que la aceptes tú en el dispositivo.

Para un teléfono con **Depuración inalámbrica**, abre **Emparejar dispositivo con código** en Android, introduce en la web su IP:puerto y código temporal, pulsa **Emparejar** y luego usa en **Conectar** el segundo IP:puerto que muestra Android. El código se utiliza una vez y no se persiste.

Puedes diagnosticar la conexión desde PowerShell:

```powershell
scripts/check-emulator.ps1
scripts/check-emulator.ps1 -Connect -Address host.docker.internal:5555
```

Cada conexión, calibración, plan, aprobación, pulsación manual y cancelación queda registrada localmente. La captura/OCR sirve para inspección; no extrae ni guarda contraseñas. Consulta [docs/USER_GUIDE.md](docs/USER_GUIDE.md) para el flujo detallado.

## Ollama en Docker

Ollama se inicia con el resto del proyecto. La primera vez, descarga el modelo configurado dentro de su volumen persistente:

```bash
docker compose up --build -d
docker compose exec ollama ollama pull qwen2.5:3b
```

Cambia `OLLAMA_MODEL` en `.env` por otro modelo ya instalado y reinicia el backend. El chat solo consulta un resumen controlado de conteos, distribución de medias, duplicados destacados y requisitos DCP; no ejecuta cambios. Preguntas y respuestas se almacenan únicamente en PostgreSQL local. Si Ollama falla, se muestra el aviso de degradación y el resto continúa activo.

La pantalla **IA** incluye además un **Análisis DCP guiado** que no depende de Ollama: pregunta qué segmento calcular, si debe conservar titulares y cuántas propuestas mostrar. OR-Tools genera soluciones reales excluyendo cartas protegidas y el análisis nunca consume cartas. Para crear un borrador de plan exige `CREAR PLAN <segmento>`; su ejecución todavía requiere `PREPARAR <plan>` en Emulador y la entrega final permanece manual.

En Windows/WSL2 el servicio reserva una GPU NVIDIA para evitar que la inferencia recaiga sobre la RAM del sistema. `OLLAMA_KEEP_ALIVE=2m` conserva velocidad durante una conversación y descarga el modelo después de dos minutos inactivo; `OLLAMA_MAX_LOADED_MODELS=1` impide modelos simultáneos, `OLLAMA_NUM_PARALLEL=1` limita el crecimiento del contexto y `OLLAMA_NO_CLOUD=1` conserva el asistente en modo local. Tras una consulta, `docker compose exec ollama ollama ps` debe mostrar uso de GPU; si no aparece, revisa el controlador NVIDIA y la integración GPU de Docker Desktop.

Si durante una sesión larga de ADB no vas a usar el chat, puedes liberar también la memoria base de Ollama con `docker compose stop ollama` y recuperarlo después con `docker compose start ollama`; inventario, DCP y emulador continúan funcionando.

## Uso esencial

### Inventario

En **Club**, crea o edita cartas, filtra, protege y realiza eliminación lógica. Importa CSV o Excel con las columnas `name,rating,position,league,club,nationality` y, opcionalmente, `card_type,rare,special,tradable,price,chemistry,protected,duplicate_untradeable`. Primero se muestra una revisión y solo se persiste al confirmar. Los botones de exportación generan CSV o XLSX.

### DCP

En **DCP**, crea un desafío y su segmento básico o usa los ejemplos. Pulsa **Optimizar** para obtener hasta tres alternativas reales. Cada resultado muestra media, química, coste y duplicados. La simulación no toca el inventario. **Confirmar entrega** consume las cartas tras una segunda confirmación; el identificador de entrega permite restaurar el estado exacto desde Ajustes.

Las cartas protegidas se excluyen. El optimizador prioriza duplicados intransferibles y penaliza transferibles, media excesiva, cartas útiles, especiales y titulares.

### Capturas y registro manual

En **Ajustes**, selecciona JPEG, PNG o WebP. OpenCV preprocesa la imagen y Tesseract propone nombre, media y posición con confianza aproximada. Nada se guarda automáticamente: corrige y registra la carta desde Club. El OCR es una ayuda, no una garantía de reconocimiento.

### Copias de seguridad

`scripts/backup.ps1` produce un dump PostgreSQL, un CSV del inventario y un JSON de configuración. `restore.ps1` exige que el archivo esté dentro de `./backups/`, crea primero otro dump de seguridad, restaura y reinicia el backend.

## Pruebas

```bash
docker compose run --rm --no-deps backend pytest -q
docker compose run --rm frontend-test
docker compose run --rm frontend-e2e
```

Playwright está configurado para iPhone 13 y su imagen de prueba incluye el navegador, por lo que no requiere instalarlo en el host. Consulta [docs/TESTING.md](docs/TESTING.md).

## Solución de problemas

- Puerto ocupado: cambia `APP_PORT` o `POSTGRES_PORT` en `.env`.
- Backend no saludable: ejecuta `docker compose logs backend database`.
- Base sin iniciar: espera al health check de PostgreSQL y revisa espacio disponible.
- Ollama sin modelo: ejecuta el comando `ollama pull` anterior; no bloquea la aplicación.
- ADB sin dispositivo: inicia un emulador/teléfono con ADB por TCP, revisa su puerto y ejecuta `scripts/check-emulator.ps1 -Connect -Address host.docker.internal:5555`.
- Coordenadas ADB incorrectas: no ejecutes el plan; toma una captura desde **Emulador** y repite la calibración para esa resolución.
- OCR débil: usa una captura nítida, recortada y de buen contraste, o registra/importa manualmente.
- Reinicio limpio conservando datos: `docker compose down` seguido de `docker compose up --build -d`.

## Seguridad y alcance

La aplicación está pensada para una red local confiable, restringe CORS, valida entradas, limita archivos, usa ORM parametrizado, nombres seguros, errores sin trazas y cabeceras de seguridad. No la expongas directamente a Internet. No es una aplicación oficial, afiliada ni aprobada por Electronic Arts. No implementa compras, ventas, partidos, scraping autenticado ni entregas finales automáticas. La preparación ADB solo reproduce un plan revisable y siempre se detiene antes de la acción irreversible.

Documentación adicional: [arquitectura](docs/ARCHITECTURE.md), [guía](docs/USER_GUIDE.md), [optimizador](docs/OPTIMIZER.md), [seguridad](docs/SECURITY.md), [pruebas](docs/TESTING.md) y [limitaciones](docs/KNOWN_LIMITATIONS.md).
