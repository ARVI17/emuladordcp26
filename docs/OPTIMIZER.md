# Optimizador DCP

El motor usa OR-Tools CP-SAT. Cada jugador candidato es una variable binaria y el objetivo minimiza una función entera de coste. Se excluyen cartas eliminadas, IDs prohibidos y protegidos, salvo una autorización individual enviada explícitamente a la API.

## Restricciones

El modelo soporta cantidad exacta, media mínima, química mínima registrada, raros, especiales, tipos de carta, puestos, ligas/clubes/naciones requeridos, mínimos y máximos de categorías distintas, IDs obligatorios/excluidos y valor total máximo. Después de resolver, `validate_solution` vuelve a comprobar la plantilla; una solución con infracciones nunca se devuelve como válida.

## Coste

La puntuación combina precio, penalización de transferibles, exceso de media, utilidad deportiva, especiales y titulares; resta bonificación por duplicado intransferible y baja utilidad. Protegidos se excluyen en vez de depender de una penalización finita. Los coeficientes iniciales quedan en configuración local.

## Media y química

`services/rating.py` separa tres estrategias: promedio truncado, redondeo mitad arriba y techo. La predeterminada es `floor_average`. Es una aproximación configurable porque no se dispone de una especificación oficial estable para todas las ediciones.

La química usa el valor 0–3 registrado en cada carta y suma el equipo. No reproduce todavía todas las reglas de enlaces, técnicos o variantes de cada edición; la interfaz y la documentación no la presentan como cálculo oficial.

## Simulación y entrega

Optimizar no modifica datos. Confirmar vuelve a validar contra el estado actual, rechaza protegidos, guarda un snapshot y aplica eliminación lógica. Restaurar revierte `deleted`, el estado de duplicado y la finalización del segmento.
