<div align="center">

# ⚽ FC Club Lab · Asistente local de plantillas y DCP

### Inventario de cartas · Optimización · Visión por computador · IA local

**Un entorno experimental para planificar tu club, revisar cartas y preparar soluciones a desafíos de creación de plantillas (DCP/SBC).**

![Python](https://img.shields.io/badge/Python-FastAPI-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-TypeScript-149ECA?logo=react&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Datos-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Local-2496ED?logo=docker&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-IA%20local-222222)
![Estado](https://img.shields.io/badge/Proyecto-En%20desarrollo-F59E0B)

[**Instalación**](#inicio-en-un-comando) · [**Emulador Android**](#emulador-o-teléfono-android-por-adb) · [**Guía de uso**](docs/USER_GUIDE.md)

</div>

---

## 🧭 Vista general

| Módulo | Función |
| --- | --- |
| 🃏 Inventario | Registrar, importar, proteger, filtrar y exportar cartas. |
| 🧩 DCP / SBC | Calcular alternativas con un optimizador determinista. |
| 📷 Capturas y OCR | Extraer propuestas de datos para revisión manual. |
| 🧠 IA local | Asistente basado en Ollama con datos acotados del inventario. |
| 📱 ADB | Preparación asistida en emulador o dispositivo autorizado, con confirmaciones. |
| 🗄️ Persistencia | PostgreSQL, migraciones y copias de seguridad. |

> **Alcance:** Proyecto no oficial. La documentación actual describe un asistente local; no garantiza conexión a cuentas reales de EA ni automatización integral. No compartas contraseñas, cookies o tokens.

<details>
<summary><strong>📚 Documentación técnica completa e instrucciones originales</strong></summary>

# emuladordcp26 — Asistente local FC 26

Aplicación local, mobile-first y no oficial para administrar un club ficticio, proteger cartas, organizar plantillas y objetivos, importar inventario, revisar capturas con OCR y resolver DCP mediante optimización determinista. Puede preparar en un teléfono o emulador Android conectado por ADB una combinación ya calculada, siempre con autorización explícita y deteniéndose antes de la entrega final. El frontend consume una API FastAPI real y toda la información se persiste en PostgreSQL local.

No inicia sesión ni se conecta directamente a las API de EA. Nunca solicita correo, contraseña, cookies, tokens ni códigos de verificación. La sesión, si se usa la preparación asistida, permanece dentro del dispositivo controlado por su propietario.

## Requisitos

- Windows 10/11, macOS o Linux con Docker Desktop/Engine y Docker Compose.
- 4 GB de RAM libres para la aplicación base; 8 GB recomendados.
- 12 GB o más de RAM si se usa Ollama junto con un emulador Android. El modelo `qwen2.5:3b` necesita además varios GB de disco.
- Puertos libres: `8080` para la aplicación y `55432` para PostgreSQL. Ambos se pueden cambiar en `.env`.

En Windows, instala Docker Desktop, activa WSL 2 cuando el instalador lo solicite y espera a que Docker indique que el motor está listo.

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

Opcionalmente copia `.env.example` a `.env` y modifica los valores locales. No confirmes `.env` en Git. Las variables principales son `APP_PORT`, `POSTGRES_PORT`, `POSTGRES_PASSWORD`, `OLLAMA_MODEL`, `OLLAMA_URL`, `ADB_ENABLED`, `ADB_DEFAULT_ADDRESS`, `MAX_UPLOAD_MB` y `CORS_ORIGINS`.

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

El backend incluye el cliente ADB dentro de su propio contenedor. El emulador o teléfono debe ofrecer ADB por TCP y ser accesible desde Docker; el valor predeterminado es `host.docker.internal:5555`. No instales credenciales en el proyecto ni las escribas en sus formularios.

1. Inicia el emulador y activa su acceso ADB local/TCP.
2. En **Emulador**, pulsa **Conectar** y comprueba que el dispositivo figure como disponible.
3. Abre manualmente la pantalla de DCP en la aplicación del dispositivo.
4. Calibra las coordenadas de búsqueda, campo, resultado y botón de agregar según la resolución mostrada.
5. Desde una solución DCP, pulsa **Preparar en emulador**. Revisa el plan y escribe `PREPARAR <id>` para autorizar sus pulsaciones.
6. Comprueba visualmente los once jugadores. La entrega final queda deliberadamente pendiente para que la aceptes tú en el dispositivo.

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

Cambia `OLLAMA_MODEL` en `.env` por otro modelo ya instalado y reinicia el backend. El chat solo consulta un resumen controlado del inventario; no ejecuta cambios. Preguntas y respuestas se almacenan únicamente en PostgreSQL local. Si Ollama falla, se muestra el aviso de degradación y el resto continúa activo.

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


</details>
