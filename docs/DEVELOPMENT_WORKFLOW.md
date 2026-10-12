# Desarrollo por sprints: FC27

El producto público es exclusivamente FC27: [frontera de edición](FC27_EXCLUSIVE.md). Conservar históricos ocultos y probar cruces solo en bases desechables. Las referencias no crean posesión. La revisión manual no acredita una variante ni una conexión EA.

Cada sprint tiene 1–3 objetivos funcionales, un solo agente por defecto, riesgos concretos y pruebas previstas. Revisa `git status --short`, rama, remotos, PR abiertas, [AGENTS.md](../AGENTS.md) y [PROJECT_MAP.md](PROJECT_MAP.md). Las PR #2 y #3 son ramas revisables, no evidencia de despliegue o merge. Conserva el trabajo ajeno y desarrolla fuera de `main`.

## Verificación aislada desde PowerShell

```powershell
python scripts/verify_docker.py --scope full
# Cambios exclusivamente backend o frontend:
python scripts/verify_docker.py --scope backend
python scripts/verify_docker.py --scope frontend
```

Requiere Python y Docker Compose. Usa un motor local, proyecto aleatorio `emuladordcp26-check-*`, imágenes propias y puerto loopback 8082 (`--port` permite otro distinto de los habituales). Construye imágenes, inicia PostgreSQL/API/frontend/Nginx, espera salud, comprueba HTTP y migraciones. Pytest usa **otra base PostgreSQL** distinta de la API de navegador. Ambas viven en tmpfs; no contienen datos únicos. Full ejecuta Pytest, Vitest y Playwright móvil/escritorio; el build del frontend forma parte de todos los scopes.

El comando rechaza volúmenes persistentes, montajes inesperados, redes externas y bases incorrectas. Retira únicamente los IDs completos de contenedores y redes propios tras verificar sus etiquetas, imágenes y montajes, sin borrar volúmenes. Un bloqueo compartido en `~/.fc27/verification/` impide pruebas simultáneas entre worktrees; el sistema operativo lo libera tras una caída. No reinicia ni despliega el principal. Comprueba sus IDs/fechas de arranque antes y después. Tras una caída abrupta, recupera solo recursos cuya propiedad y carácter sintético coinciden con su manifiesto local. Una discrepancia conserva el recurso y detiene la limpieza.

No ejecutes restauraciones adicionales en el contenedor `test-database` mientras corre Pytest: su tmpfs y WAL también consumen el límite de 512 MB. Las comprobaciones de dump/migración poblada deben ser secuenciales o usar otro contenedor desechable con recursos propios. Un fallo por memoria no cuenta como prueba pasada; conserva el informe y repite la suite aislada.

Las pruebas generales usan un catálogo sintético explícito en `backend/tests/catalog_fixture.py`. El servidor E2E `tests/e2e_app.py` exige la variable de prueba y una base permitida; solo peticiones preparatorias con `X-Catalog-Fixture: 1` crean evidencia sintética. `app.main` y el arranque normal nunca importan ese arnés. Las pruebas `catalog_boundary` y el recorrido `catalog.spec.ts` lo omiten para comprobar la política real de admisión. Un pase con fixtures no prueba autenticidad de datos ni acceso a EA.

La cabecera de fixtures también limita la evidencia de definiciones mediante contexto de petición; una creación desde la interfaz normal queda pendiente. El PostgreSQL destructivo conserva512MB de límite, shared_buffers32MB y WAL64MB con checkpoints cada30s para que las sucesivas recreaciones del esquema no agoten el tmpfs.

Logs y resultado PASSED/FAILED: `state/sprints/emuladordcp26-check-*/`. `docker-compose.review.yml` es una pieza interna del arnés temporal; no se inicia como segunda instalación personal. La comprobación real del cierre tras éxito, error, cancelación y caída se ejecuta con `python scripts/check_test_lifecycle.py`.

## Cierre de cada sprint

1. Pruebas pertinentes, integración Docker, `git diff --check` y revisión de secretos/datos en el diff.
2. Commit descriptivo y push a la rama de trabajo; comparar `git rev-parse HEAD` con `git ls-remote origin refs/heads/<rama>`.
3. Abrir/actualizar PR en borrador y revisar CI. Un push no despliega ni autoriza un merge.
4. Registrar en `state/sprints/`: objetivo, cambios, comandos/resultados, rama/commit/SHA remoto, respaldo, bloqueos y siguiente paso. Un fallo o dependencia se marca WIP/NO DISPONIBLE; no inventar un pase.

`state/`, `.env`, dumps, logs, capturas, credenciales e inventarios personales permanecen fuera de Git. `state/ENTORNO_LOCAL.md` registra motor, repositorios, contenedores, mounts reales, volúmenes y ubicación de respaldos sin secretos. Las rutas internas `/var/lib/docker/volumes/...` pertenecen al motor Linux; no se traducen en rutas Windows inventadas.

## Persistencia y recuperación

El principal conserva `emuladordcp26_postgres_data` y `emuladordcp26_ollama_data`. Antes de migrarlo: autorización específica, dump en `backups/`, restauración comprobada en otra base y plan para recuperar código/esquema concordantes. No ejecutar el downgrade que elimina contexto ni restaurar primero sobre datos únicos. Las [migraciones documentadas](FC27_UPGRADE.md) conservan las dos variantes históricas de `0005`.

Retirar un contenedor no equivale a respaldar su capa escribible: inspecciona diff, mounts, datos y configuración antes. Conserva volúmenes, bind mounts y archivos únicos; si no es posible preservarlos, deja ese contenedor pendiente. Las reglas de este documento no autorizan eliminar otros proyectos, operar cartas EA ni publicar la aplicación.

## Operación personal única

`powershell -File scripts/fc27.ps1 Inicio|Estado|Pruebas|Parada` usa el proyecto canónico `emuladordcp26`, IDs existentes y el volumen `emuladordcp26_postgres_data`. Resuelve su código por ruta absoluta, comprueba motor local, duplicados y puerto 8080. Inicio no ejecuta `up`, builds ni recreaciones: otro worktree no produce otra aplicación. Si faltan servicios, exige revisar un despliegue; no inventa un proyecto o puerto alternativo. Parada conserva contenedores y datos. Los errores nativos se verifican explícitamente.
