# Análisis de plantillas y optimización DCP

Hay dos decisiones independientes: organizar cartas propias para jugar y seleccionar cartas que el usuario podría consumir en un DCP. Ambas usan OR-Tools CP-SAT, pero sus restricciones, puntuaciones y efectos son diferentes.

Fuentes de implementación: [squad_analysis.py](../backend/app/services/squad_analysis.py), [sbc.py](../backend/app/optimizers/sbc.py), [requirements.py](../backend/app/schemas/requirements.py) y [routes.py](../backend/app/api/routes.py).

## Referencia de FC27 y alcance local

EA describe DCP simplificados que acumulan puntos de cartas, admiten duplicados y entregas parciales, y coexisten con desafíos tradicionales. También introduce Galería y caminos de evolución; las holográficas conservan los atributos de juego de su versión correspondiente. Fuente: [FUT Deep Dive, 2 de agosto de 2026](https://www.ea.com/games/ea-sports-fc/fc-27/news/pitch-notes-fc27-fut-deep-dive).

La [actualización del lanzamiento, 14 de septiembre de 2026](https://www.ea.com/es/games/ea-sports-fc/fc-27/news/pitch-notes-fc27-launch-update) publica una referencia de puntuaciones. El proyecto conserva esa referencia y su fecha en [fc27_content.json](../backend/app/data/fc27_content.json), pero exige que se revise el valor final de cada carta. No deduce bonificaciones desconocidas por rareza, holografía ni contenido posterior.

Los límites y pesos que siguen describen este programa local. No certifican que una combinación sea entregable en una pantalla actual de EA.

## Recomendación de plantillas

`GET /club/analysis` resume cartas disponibles de la edición activa, revisión, protección, cesiones, posiciones y huecos. Sugiere una formación por cobertura de puestos. Ese indicador no compara exhaustivamente el rendimiento de todas las tácticas.

`GET /squads/formations` devuelve las plazas exactas disponibles:

| Formación local | Puestos |
| --- | --- |
| 4-3-3 | POR, LD, DFC, DFC, LI, MCD, MC, MC, ED, DC, EI |
| 4-4-2 | POR, LD, DFC, DFC, LI, MD, MC, MC, MI, DC, DC |
| 4-2-3-1 | POR, LD, DFC, DFC, LI, MCD, MCD, MCO, MCO, MCO, DC |
| 4-1-2-1-2 | POR, LD, DFC, DFC, LI, MCD, MC, MC, MCO, DC, DC |
| 3-5-2 | POR, DFC, DFC, DFC, MD, MCD, MCD, MCO, MI, DC, DC |

`POST /squads/recommend?formation=4-4-2` conserva la llamada antigua. El cuerpo opcional permite restricciones más precisas:

```json
{
  "formation": "4-3-3",
  "style": "balanced",
  "locked_player_ids": [],
  "excluded_player_ids": [],
  "bench_size": 7,
  "include_loans": true,
  "include_unreviewed": false,
  "use_alternate_positions": true
}
```

El modelo crea variables carta/plaza únicamente para posiciones principales o alternativas registradas. Cada plaza recibe como máximo una carta y cada carta ocupa como máximo una plaza. Los IDs fijados deben aparecer en el once; si no caben, la petición se rechaza. Las cartas protegidas siguen disponibles para jugar.

La misma identidad base, carta o nombre normalizado no se repite en el once ni en el banquillo. Cuando faltan identificadores, el nombre ayuda a excluir versiones repetidas, pero puede confundir homónimos o abreviaturas. La respuesta avisa de esta limitación.

Cubrir once puestos válidos domina cualquier mejora del encaje. Los huecos se devuelven de forma explícita, sin resolverlos colocando futbolistas fuera de posición. El banquillo se selecciona después del once mediante una heurística que favorece cobertura de portería, defensa, medio y ataque; no es una optimización conjunta de todas las sustituciones.

### Encaje y explicaciones

La puntuación local combina un 70 % de media y un 30 % de atributos disponibles, ponderados por puesto. Si faltan todos los atributos relevantes, usa solo la media. Por ejemplo, en DFC pesan especialmente defensa y físico; en DC, tiro y ritmo; en POR, los atributos de portería.

Los estilos `attacking` y `defensive` ajustan esos pesos. Un rol registrado como `+` o `++` en la clave de posición añade un ajuste pequeño; cada PlayStyle+ registrado añade 0,25, hasta tres. Los nombres de PlayStyles o las instrucciones tácticas no se simulan. La holografía no recibe un bono de rendimiento.

Cada plaza devuelve puntuación, carta, uso de posición alternativa y una explicación de sus datos. La química es la suma registrada de las cartas, con `chemistry_approximate=true`; no se recalcula una química oficial dependiente de compañeros o técnico.

La asignación dispone de cuatro segundos. Una solución factible sin prueba de optimalidad lo indica; agotar el tiempo sin solución tampoco demuestra que el club carezca de una combinación válida.

## DCP: requisitos tipados

`normalize_requirements()` comparte el mismo esquema entre creación, optimización y confirmación. Rechaza claves desconocidas, IDs repetidos o contradictorios, tipos incorrectos y límites incompatibles. `kind` omitido significa `traditional` para conservar los requisitos antiguos.

### Formato tradicional

Admite tamaño exacto de 1 a 23, media y química mínimas, raros/especiales, mínimos y máximos de ligas/clubes/nacionalidades, categorías concretas, posiciones principales, IDs obligatorios/excluidos y valor máximo. Ejemplo:

```json
{
  "kind": "traditional",
  "squad_size": 11,
  "min_rating": 82,
  "rating_strategy": "floor_average",
  "min_chemistry": 15,
  "required_nation": "España",
  "min_from_nation": 2,
  "max_leagues": 4,
  "max_total_value": 25000
}
```

Los requisitos `min_rare` y similares se conservan como restricciones locales y para compatibilidad histórica. No son una plantilla oficial universal para FC27.

Las posiciones de un DCP tradicional cuentan el campo principal de cada carta; ese requisito no ejecuta el asignador de posiciones alternativas del analizador de fútbol.

### Formato por puntos

```json
{
  "kind": "score",
  "target_score": 100,
  "min_item_rating": 1,
  "max_items_per_submission": 23
}
```

Cada copia debe tener `gallery_score` positivo y `data_reviewed=true`. El límite de 23 es una capacidad local por lote, no una afirmación sobre el máximo de una interfaz de EA.

El objetivo puede cubrirse en varios lotes. `current_score` se calcula sumando `Submission.score_contribution` de las entregas activas: un cliente no puede introducir progreso arbitrario. La respuesta distingue contribución, progreso proyectado, puntos pendientes, `partial` y `will_complete`.

Si se definen `required_player_ids`, los aún no entregados son obligatorios en el siguiente lote; los ya aportados no bloquean posteriores entregas. `max_total_value` resta el valor de las entregas activas del segmento, impidiendo exceder el presupuesto total dividiéndolo en lotes. Restaurar recupera también esa parte del presupuesto.

El solver busca primero una contribución alta que respete el límite del lote. Después minimiza la puntuación de preservación manteniendo suficientes puntos para completar, o para alcanzar la mejor contribución que encontró. Una propuesta parcial no es una demostración matemática de que resulte imposible completar el objetivo con otra selección.

## Candidatos, valor y coste de selección

La selección DCP excluye cartas eliminadas, cedidas, pendientes de revisión, de otra edición, excluidas o protegidas efectivamente. `allow_protected_ids` solo permite incluir IDs específicos en una simulación; confirmar sigue rechazando cartas protegidas.

`total_cost` es la suma de precios registrados, sin penalizaciones artificiales. `optimization_score` es la función entera que el solver minimiza:

| Componente | Ajuste local |
| --- | ---: |
| Precio registrado | +precio |
| Carta transferible | +1.500 |
| Cada punto de media por encima del mínimo aplicable | +650 |
| Cada punto de utilidad | +120 |
| Carta especial | +50.000 |
| Titular marcado | +200.000 |
| Duplicado intransferible | −8.000 |
| Utilidad menor de 15 | −1.000 |

Cada coste individual tiene mínimo 1. En modo score, el mínimo aplicable es `min_item_rating`; en tradicional, `min_rating`. Estos coeficientes están codificados en `_cost()`. El ajuste `app_settings.optimizer` es informativo y no reconfigura automáticamente esa función.

Se calculan hasta cinco soluciones diferentes. Cada invocación CP-SAT dispone de cinco segundos; el modo score utiliza dos fases por alternativa. El tiempo total de una petición puede superar cinco segundos. Toda solución se comprueba de nuevo con `validate_solution()` antes de devolverse como válida. No encontrar una solución dentro de los límites no prueba que el problema sea imposible.

## Media y química tradicional

[rating.py](../backend/app/services/rating.py) implementa promedio truncado, mitad arriba y techo: `floor_average`, `round_half_up` y `ceiling`. El modelo traduce la media mínima a una suma mínima coherente con la estrategia y el validador comprueba el resultado con la misma regla.

Son aproximaciones locales. La química suma valores registrados 0–3 y no implementa todos los efectos de técnico, posición o vínculos. El hecho de superar el validador significa que se cumplen los datos y reglas locales introducidos.

## Confirmación y restauración

Optimizar no escribe. Confirmar exige una acción explícita y vuelve a consultar edición, disponibilidad, revisión, protección, requisitos y progreso bajo la reserva común de inventario. Se registran el valor real, la contribución de puntos y un snapshot con identidad, datos de revisión y estados restaurables.

Cada copia pasa a estar consumida por el ID de esa entrega. Dos segmentos que intentan usar la misma copia no pueden confirmar ambos a través de las rutas cooperativas. Restaurar valida todos los propietarios antes de cambiar los flags y rechaza entregas antiguas ambiguas. El avance de otros lotes del mismo segmento se conserva.

La restauración afecta únicamente a la base local. La entrega final en Companion se decide y realiza por separado; ADB no prepara actualmente el formato score ni automatiza el botón final.

## Galería y evoluciones

[evaluate_set()](../backend/app/services/gallery.py) usa el historial local, reglas revisadas y etiquetas para seleccionar entradas de Galería. Si faltan puntuaciones o revisión, la respuesta no inventa una nota oficial. El historial puede incluir cartas ya consumidas localmente y no representa inventario disponible para un DCP.

[preview_path()](../backend/app/services/evolutions.py) comprueba requisitos revisados y proyecta una cadena seleccionada de caminos. Detiene la cadena al encontrar incompatibilidad, dato imprescindible desconocido o vencimiento. La proyección no activa la evolución, no modifica la carta y deja su puntuación evolucionada pendiente de revisión.
