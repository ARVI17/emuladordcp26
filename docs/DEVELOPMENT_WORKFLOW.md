# Desarrollo por sprints: FC27

Cada sprint tiene 1–3 objetivos funcionales, un solo agente por defecto, riesgos concretos y pruebas previstas. Revisa `git status --short`, rama, remotos, PR abiertas, [AGENTS.md](../AGENTS.md) y [PROJECT_MAP.md](PROJECT_MAP.md). Las PR #2 y #3 son ramas revisables, no evidencia de despliegue o merge. Conserva el trabajo ajeno y desarrolla fuera de `main`.

## Verificación aislada desde PowerShell

```powershell
python scripts/verify_docker.py --scope full
# Cambios exclusivamente backend o frontend:
python scripts/verify_docker.py --scope backend
python scripts/verify_docker.py --scope frontend
```

Requiere Python y Docker Compose. Usa un motor local, proyecto aleatorio `emuladordcp26-check-*`, imágenes propias y puerto loopback 8082 (`--port` permite otro distinto de los habituales). Construye imágenes, inicia PostgreSQL/API/frontend/Nginx, espera salud, comprueba HTTP y migraciones. Pytest usa **otra base PostgreSQL** distinta de la API de navegador. Ambas viven en tmpfs; no contienen datos únicos. Full ejecuta Pytest, Vitest y Playwright móvil/escritorio; el build del frontend forma parte de todos los scopes.

El comando rechaza volúmenes persistentes, montajes inesperados, redes externas y bases incorrectas. Retira únicamente su proyecto al terminar, incluso al fallar, mediante `down` sin `-v`. No reinicia ni despliega el principal. Comprueba sus IDs/fechas de arranque antes y después. Si se interrumpe abruptamente, consulta el proyecto exacto del informe antes de retirar contenedores. Nunca uses un borrado global.

Logs y resultado PASSED/FAILED: `state/sprints/emuladordcp26-check-*/`. Los datos de prueba se descartan deliberadamente. Para revisar una interfaz a mano existe `docker-compose.review.yml` en 8081: también es desechable; detener su PostgreSQL tmpfs pierde datos. No confundas esa revisión con el club real ni con el stack principal.

## Cierre de cada sprint

1. Pruebas pertinentes, integración Docker, `git diff --check` y revisión de secretos/datos en el diff.
2. Commit descriptivo y push a la rama de trabajo; comparar `git rev-parse HEAD` con `git ls-remote origin refs/heads/<rama>`.
3. Abrir/actualizar PR en borrador y revisar CI. Un push no despliega ni autoriza un merge.
4. Registrar en `state/sprints/`: objetivo, cambios, comandos/resultados, rama/commit/SHA remoto, respaldo, bloqueos y siguiente paso. Un fallo o dependencia se marca WIP/NO DISPONIBLE; no inventar un pase.

`state/`, `.env`, dumps, logs, capturas, credenciales e inventarios personales permanecen fuera de Git. `state/ENTORNO_LOCAL.md` registra motor, repositorios, contenedores, mounts reales, volúmenes y ubicación de respaldos sin secretos. Las rutas internas `/var/lib/docker/volumes/...` pertenecen al motor Linux; no se traducen en rutas Windows inventadas.

## Persistencia y recuperación

El principal conserva `emuladordcp26_postgres_data` y `emuladordcp26_ollama_data`. Antes de migrarlo: autorización específica, dump en `backups/`, restauración comprobada en otra base y plan para recuperar código/esquema concordantes. No ejecutar el downgrade que elimina contexto ni restaurar primero sobre datos únicos. Las [migraciones documentadas](FC27_UPGRADE.md) conservan las dos variantes históricas de `0005`.

Retirar un contenedor no equivale a respaldar su capa escribible: inspecciona diff, mounts, datos y configuración antes. Conserva volúmenes, bind mounts y archivos únicos; si no es posible preservarlos, deja ese contenedor pendiente. Las reglas de este documento no autorizan eliminar otros proyectos, operar cartas EA ni publicar la aplicación.
