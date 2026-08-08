# Pruebas

## Backend

Pytest crea una base SQLite temporal limpia por caso y carga el seed. Sus 30 casos comprueban health, seed, panel, CRUD/protección/eliminación, plantillas, objetivos, importación/exportación, degradación sin Ollama, DCP válido e imposible, exclusión de protegidos, duplicados, simulación, confirmación/restauración, emparejamiento ADB sin fuga del código, planes, lectura revisable del club, jerarquía temporal acotada, navegación validada, continuación por lotes, importación parcial por candidatos y extracción de requisitos.

```bash
docker compose run --rm --no-deps backend pytest -q
```

Para comprobar migraciones PostgreSQL con el stack activo:

```bash
docker compose exec backend alembic current
docker compose exec database psql -U fc26 -d fc26 -c "select count(*) from players;"
```

El head actual es `0004`. Para una migración limpia usa una base temporal separada, ejecuta `alembic upgrade head`, comprueba sus tablas y elimina solamente esa base de prueba.

## Frontend

Vitest prueba utilidades de presentación y la compilación TypeScript ocurre durante la imagen. Playwright define un proyecto iPhone 13 para navegación esencial.

```bash
docker compose run --rm frontend-test
docker compose run --rm frontend-e2e
```

El servicio `frontend-e2e` incluye Playwright y prueba la SPA contra Nginx en la red interna con emulación de iPhone 13. Actualmente hay 2 casos Vitest y 2 casos Playwright, incluido el límite de entrega manual de la pantalla Emulador.

## Verificación manual mínima

Confirma que `/health`, `/api/dashboard`, `/api/docs` y `/` respondan 200; crea una carta, protégela, simula un DCP, comprueba que la simulación no reduzca inventario, confirma otra solución y restaura su ID. Prueba la interfaz a 390 px de ancho y ambos temas.

Para ADB, verifica primero `/api/emulator/status` sin dispositivo: debe degradarse sin afectar el resto. Con un dispositivo desechable, calibra, prepara un plan, prueba una frase incorrecta, ejecuta/cancela y confirma visualmente que ningún paso pulse la entrega final. No hagas esta prueba sobre una plantilla o cuenta con elementos que no puedas recuperar.

La suite simula además un dispositivo para comprobar sesión de lectura, captura duplicada, revisión, frase errónea, archivo preciso de la demo e importación. La compatibilidad visual con una versión concreta de Companion requiere todavía una prueba manual con hardware.
