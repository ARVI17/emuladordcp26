# Observaciones de mercado y agenda conjunta

Mercado permite configurar la comisión supuesta, costes adicionales e incremento revisado. Conserva el neto esperado, escenario adverso y equilibrio; la tasa/redondeo siguen siendo hipótesis, sin confirmar reglas oficiales. Ningún cálculo aumenta el saldo ni acredita una venta.

`GET /market/series` exige variante, mercado y tipo de observación; usa exclusivamente la edición y club activos. Devuelve hasta 200 cotizaciones en orden de fecha observada, enlaces, cobertura y caducidad. No interpola, predice ni infiere volumen. Todas las cotizaciones de este flujo son revisión manual, no un proveedor conectado.

`GET/POST /market/alerts` y `PATCH /market/alerts/{id}` guardan condiciones locales. Se evalúa únicamente la observación más reciente del mismo grupo; si caducó no se reemplaza silenciosamente por una anterior. Se muestran alertas al abrir/actualizar la página, sin procesos externos ni operaciones de mercado. Máximo 50 alertas activas por edición; lectura paginada de 50, activas primero. La migración `0012` añade las definiciones sin alterar cartas, cotizaciones o diario.

En Planes, `POST /plans/compare` contrasta dos borradores vigentes: gasto máximo, copias exactas compartidas, ventas/consumos previstos, valor local conocido y precios ausentes. Ese valor no equivale a cotización vigente. Son alternativas: comparar no autoriza ni reserva ambas.

`POST /plans/agenda` recibe presupuesto, reserva y hasta 20 IDs prioritarios. Examina los últimos 100 borradores/revisados, revalida entrada, inventario, reglas y cotizaciones; respeta compromisos existentes y asigna una copia a una sola ruta seleccionada. Después de la prioridad indicada ordena por plazo. La selección es secuencial y conservadora, no una optimización global ni un calendario que conozca el tiempo de juego. Devuelve los objetivos locales como recordatorios separados, sin certificar progreso remoto ni atribuir recompensas. Los planes conservan todos sus pasos y aprobación específica.

La respuesta es una simulación en el momento del cálculo: no crea reservas. Una modificación posterior exige recalcular y las rutas de revisión/reserva/confirmación vuelven a validar. `POST /plans/{id}/refresh` reconstruye un borrador desde los mismos IDs contra el estado actual y guarda una nueva propuesta sin aprobación. Si faltan cartas o requisitos, exige corregir la selección; no sustituye cartas automáticamente. El borrador anterior permanece disponible para cancelar o revisar su historial.
