# Reglas FC27 y límites de validación

Corte documental: 5-nov-2026. La [ayuda oficial de DCP](https://help.ea.com/en/articles/ea-sports-fc/sbcs/) distingue Puzzle y Simplified, describe contribuciones Item Score y entregas múltiples. La [actualización de lanzamiento](https://www.ea.com/games/ea-sports-fc/fc-27/news/pitch-notes-fc27-launch-update) relaciona puntuación con OVR, rareza y estado holográfico. Esto **no acredita una fórmula universal numérica** para todas las cartas/revisiones.

La base 34c4e05 ya implementa reglas tipadas traditional/score, progreso parcial, solver y validador independientes. Usa puntos revisados por carta cuando están disponibles; no se añadió una tabla universal de puntos en este incremento. Los borradores leídos por OCR siguen exigiendo revisión y procedencia. Media y química siguen siendo aproximaciones locales.

La lectura del DCP y el editor manual existentes permiten preparar simulaciones. Escanear inventario no certifica automáticamente rareza, cesión, transferibilidad, variante, requisitos ni vigencia. `missing_for_dcp` excluye cartas cuyo metadato requerido es desconocido.

Pendiente: medición con capturas reales de un DCP tradicional y uno simplificado; evidencia numérica/versionada de Item Score; estado OPTIMAL/FEASIBLE_NOT_PROVEN/cotas; compras externas y presupuesto lexicográfico. No llamar «mínimo del mercado» al coste heurístico existente.

EA señala que las cartas enviadas se retiran permanentemente. Un snapshot/restauración de este programa solo afecta datos locales; nunca restaura cartas EA ni pulsa el submit final.
