# Actualización FC27 y contenido revisable

## Alcance de esta versión

La versión vigente solo ofrece FC27 y conserva otras ediciones ocultas, con metadatos de cartas, análisis del club, Galería histórica, evolución por caminos/cadenas y DCP por puntuación revisada. Esta revisión utiliza formaciones documentadas vigentes y añade los planes descritos en [FC27_PLANNER.md](FC27_PLANNER.md). Las definiciones pueden conservarse como borradores; activarlas requiere acreditar la fuente, reglas exactas y vigencia. Las migraciones 0013/0014 preservan datos legados sin declararlos verificados. Consulta [FC27_EXCLUSIVE.md](FC27_EXCLUSIVE.md).

Las fuentes incorporadas son el [FUT Deep Dive](https://www.ea.com/games/ea-sports-fc/fc-27/news/pitch-notes-fc27-fut-deep-dive) y la [actualización del lanzamiento](https://www.ea.com/games/ea-sports-fc/fc-27/news/fc-27-fut-developer-launch-update) de EA, revisadas el **12 de octubre de 2026 UTC**. `backend/app/data/fc27_content.json` conserva fechas, enlaces y vigencia. La tabla base no acreditada se retiró; no se infieren bonificaciones ni se descargan datos privados.

## Actualizar una instalación con datos

`0010` añade `squads.tactic` sin eliminar plantillas, jugadores ni consumo. En instalaciones nuevas, la histórica `0001` puede haber creado esa columna desde el modelo actual; `0010` reconoce ese caso sin editar migraciones anteriores. Se contrastó también la actualización desde un dump real de pruebas en `0009`.

Crea primero un dump con `scripts/backup.ps1` y comprueba que exista. Actualiza el código a la versión revisada y ejecuta:

```bash
docker compose up --build -d
docker compose exec backend alembic current
docker compose exec backend alembic check
```

La revisión esperada es `0014`. Mantén `emuladordcp26_postgres_data` y los demás nombres técnicos existentes. No borres volúmenes ni cambies `POSTGRES_DB` para pasar a FC27.

`0011` incorpora la agenda de práctica y separa el diario de partidos por edición. Conserva como `unverified` los registros antiguos salvo evidencia en un contexto ya verificado. Nunca deduce su edición del perfil local que puede haber cambiado. Se comprueba restaurando un dump desechable anterior y preservando sus conteos.

`0012` añade alertas locales de umbral por edición/variante/mercado/tipo. No cambia cotizaciones ni saldos. La recuperación conserva el procedimiento de restauración a esquema/código concordantes; no se aplica automáticamente a la instancia principal.

`0006` añade contextos, sesiones, snapshots, mapeos externos, planes/reservas, mercado y conocimiento; `0007` conserva indicadores remotos desconocidos; `0008` separa definiciones públicas de progreso privado; `0009` conserva edición y mercado en el diario. Ninguna migra la demo a una cuenta vinculada. Los precios cero heredados, usados como desconocidos por el editor anterior, pasan a `null`; las nuevas entradas permiten cero explícito.

Hay dos revisiones históricas llamadas `0005`: la de FC27 y la de `candidate_count` en Companion. `0006` inspecciona el esquema: si falta `players.game_version`, ejecuta el puente FC27 existente antes de ampliar contextos. Ambas rutas se comprobaron en PostgreSQL desechable, sin modificar las migraciones aplicadas. El conteo del escáner se conserva. No copies el archivo de la otra `0005` sobre una instalación aplicada.

El downgrade que eliminaría contextos está bloqueado; recuperar una versión anterior requiere restaurar el respaldo en el esquema/código correspondientes. Para una revisión aislada usa `docker-compose.review.yml`; no apliques una rama sin revisar a los datos únicos. Consulta [FC27_PLANNER.md](FC27_PLANNER.md).

La migración:

- asigna FC26 a cartas, plantillas, desafíos, objetivos, entregas y lecturas anteriores;
- activa FC27 en el perfil, sin copiar cartas entre ediciones;
- añade metadatos sin inventar atributos, puntos ni revisión de datos legacy;
- conserva consumos y asigna propietario cuando existe una única entrega confirmada verificable;
- deja pendientes de revisión los consumos antiguos ambiguos;
- cancela preparaciones ADB que no deben reanudarse automáticamente;
- conserva candidatos de lectura con IDs siguientes que no reutilizan los ya importados.

Si el backend no arranca, conserva el volumen y revisa los logs. `0005` no ofrece un downgrade destructivo: volver al código anterior exige restaurar el respaldo anterior en un entorno apropiado. No ejecutes `make reset` como solución a una migración.

El arranque normal no carga demo. Los fixtures ficticios se limitan a bases desechables y nunca representan cartas del propietario.

## Datos actuales del club

Después de la migración, el inventario FC27 estará vacío hasta que registres tus cartas reales. Puedes introducirlas, importar CSV/XLSX o revisar una lectura de Companion. No hay selector histórico: otras ediciones se conservan ocultas. Las declaraciones FC27 sin variante acreditada quedan en cuarentena.

Para recomendaciones útiles revisa, además de media/posición, posiciones alternativas, atributos, estilos, roles y estado de cesión. Para Galería/DCP por puntos registra `gallery_score` verificado. Un valor desconocido debe permanecer vacío. Las cartas antiguas FC26 no se vuelven FC27 solo por compartir nombre.

## Paquetes de conjuntos y evoluciones

En **Novedades**, carga o pega un JSON. El esquema exterior contiene:

| Campo | Uso |
| --- | --- |
| `schema_version` | `1` para este formato. |
| `game_version` | Edición del paquete, por ejemplo `FC27`; debe coincidir con la edición activa para confirmar. |
| `published_at` | Fecha ISO 8601 de la revisión. No significa que todas las reglas sean oficiales o sigan vigentes. |
| `source_url` | Fuente HTTPS opcional, solo como referencia; el backend no descarga esa URL. |
| `sets` | Hasta 100 conjuntos validados. |
| `evolutions` | Hasta 100 definiciones validadas. |

Cada elemento debe tener un `slug` estable para actualizarlo. La combinación edición + slug identifica la definición; un nombre visible puede cambiar sin crear otra si mantienes el slug. Las ediciones de todos los elementos deben coincidir. El paquete no modifica jugadores.

### Ejemplo mínimo: conjunto personalizado

Este es un **ejemplo local**, no un conjunto oficial ni una tabla de recompensas de EA:

```json
{
  "schema_version": 1,
  "game_version": "FC27",
  "published_at": "2026-10-10T00:00:00Z",
  "sets": [
    {
      "slug": "mi-coleccion-colombia",
      "name": "Mi colección de Colombia",
      "category": "Personalizado",
      "description": "Ejemplo para revisar antes de usar",
      "rules": {
        "size": 3,
        "min_rating": 75,
        "nationality": "Colombia",
        "unique_players": true
      },
      "tags": [],
      "grade_thresholds": {},
      "reward": "",
      "rules_reviewed": false
    }
  ],
  "evolutions": []
}
```

El ejemplo se conserva como borrador pendiente: no acredita reglas, umbrales ni vigencia. La evaluación requiere evidencia documental técnica; una casilla o URL no la sustituye.

### Ejemplo mínimo: evolución personalizada con tope

También es **ficticia** y no asegura elegibilidad en EA. Puede incluirse como un elemento del array `evolutions`:

```json
{
  "game_version": "FC27",
  "slug": "ejemplo-pase-local",
  "name": "Ejemplo local de pase",
  "description": "Definición didáctica; revisar antes de simular",
  "requirements": {
    "min_rating": 1,
    "max_rating": 84,
    "positions": ["MC"],
    "max_attributes": {"passing": 85}
  },
  "paths": [
    {
      "id": "pase",
      "name": "Mejorar pase",
      "upgrades": {
        "rating": 1,
        "rating_cap": 85,
        "attributes": {"passing": 3},
        "attribute_caps": {"passing": 87}
      }
    }
  ],
  "rules_reviewed": false
}
```

La app exige revisión antes de considerar verificadas esas reglas. Un aumento es una suma limitada por su tope; no es un valor final asignado. Registra caducidad, estrellas, posiciones o estilos cuando sean parte de la definición real. Hasta ocho caminos por evolución y cinco evoluciones distintas por cadena.

### Vista previa y confirmación por API

Las rutas se muestran sin el prefijo externo `/api`:

```text
POST /content/import
{ "manifest": { ... }, "confirm": false }

POST /content/import
{ "manifest": { ... }, "confirm": true, "preview_hash": "hash recibido" }
```

Ambas peticiones deben llevar el mismo manifiesto. La transacción crea o actualiza las definiciones, registra procedencia y conserva un recibo por hash. Reenviar después un paquete antiguo ya importado no revierte una revisión más reciente. Una versión nueva del paquete debe revisarse y confirmarse de nuevo.

Las validaciones completas están en [schemas/fc27.py](../backend/app/schemas/fc27.py) y la API describe los tipos en Swagger. Un cambio de requisitos no admitido debe ampliar contrato, validador y pruebas antes de importarse; no uses un campo libre para simular soporte inexistente.

## Qué se actualiza con cada mecanismo

| Cambio | Cómo incorporarlo |
| --- | --- |
| Jugadores o atributos del club | Edición/importación revisada en Club; sin sincronización autenticada. |
| Noticias públicas | Botón de actualización; conserva la última lista si falla. |
| Conjuntos y evoluciones | Editor o paquete JSON revisado con fecha/fuente. |
| DCP y sus requisitos | Editor DCP o borrador OCR revisado; el paquete actual no importa DCP. |
| Nueva fórmula o mecánica | Cambio de código, esquema si procede y pruebas; las noticias no reconfiguran el solver. |
| Cambio de interfaz Companion | Recalibración y comprobación de lectura/identidad antes de autorizar planes. |

No están implementados el Hub 3D, canje de recompensas/tokens, sincronización íntegra de campañas/eventos ni precios de mercado. Los holográficos tienen indicador y puntuación revisable; no se renderiza una réplica de todas sus animaciones. El propósito de esta versión es administrar y planificar el club con datos comprobados.

## Evidencia de verificación

La migración se probó localmente con SQLite nueva y con una base anterior de 132 cartas, incluyendo consumo, lectura parcial y un plan en ejecución. La [ejecución CI del 10 de octubre de 2026](https://github.com/ARVI17/emuladordcp26/actions/runs/38020243563), sobre el código `ba9c17b`, comprobó también la actualización desde FC26 en PostgreSQL 16, la conservación de las 132 cartas y `alembic check`. Pasaron las 111 pruebas backend, 24 pruebas frontend y 6 recorridos Chromium en móvil/escritorio; las configuraciones Compose base/GPU fueron válidas.

La CI de navegador utilizó Vite y una API con datos desechables. Quedan por ejecutar un arranque completo del stack Docker, respaldo/restauración en PowerShell y las comprobaciones con Companion real. [TESTING.md](TESTING.md) detalla el alcance y las limitaciones; estas pruebas no describen tu instalación ni utilizan tus jugadores.
