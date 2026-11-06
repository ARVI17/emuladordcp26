# Procedencia de precios

El escaneo visual nuevo no interpreta una media como monedas ni rellena `Player.price`. Un precio desconocido sigue desconocido. No se realizan consultas automáticas a proveedores ni compras.

La base FC27 conserva `MarketQuote`: edición, variant_id exacto, mercado, tipo, importe, fecha observada, fecha de importación, vencimiento, URL y cobertura. El formulario **Mercado y diario** registra observaciones manuales; su catálogo/admisión conservan los requisitos anteriores. Console y PC son mercados separados; no se debe reutilizar una cotización PC para PlayStation.

Un anuncio vigente observado no acredita que siga disponible al comprar. Una cotización caducada no es una oferta disponible. La comisión de la calculadora es una hipótesis editable, no una comisión universal verificada por este incremento. El diario solo registra una declaración contrastada del usuario; no ejecuta transacciones.

Pendiente de las etapas 3–4: importar un catálogo/precios permitido utilizable desde contexto visual, reconciliar discrepancias por variante, optimizar propias+compras y exponer `new_coins_required`, `opportunity_cost_estimate`, reposición y puntuación de protección por separado. El `total_cost` existente no se renombra a gasto de bolsillo. Hasta implementar ese modelo, no se entrega una lista de compras supuestamente óptima.
