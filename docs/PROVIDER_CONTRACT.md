# Contrato de lecturas autorizadas

Producción conserva **cero adaptadores registrados**. La [documentación oficial EA](https://help.ea.com/en/articles/ea-sports-fc/community-api/) se volvió a comprobar el 11-oct-2026: solo identifica FUTBIN, FUT.GG y FUTWIZ como socios. No documenta una concesión, scopes ni protocolo para esta aplicación. Autorizar EA sigue devolviendo «Integración pendiente» y no solicita credenciales.

`services/providers.py` define `ReadAdapter`, `ClubIdentity` y el ejecutor. Incorporar un adaptador exige evidencia de aprobación para esta aplicación, URL de documentación, permisos exactos documentados, cobertura y límite de tiempo. El registro es código revisado; no existe endpoint de registro, proveedor demo, URL arbitraria ni importación pública de lecturas verificadas. Los adaptadores sintéticos se inyectan solo en pruebas.

Una entrada real vinculada solicita lectura únicamente si existe ese adaptador y la conexión tiene los permisos requeridos. `POST /club-contexts/{id}/sync-runs` inicia o devuelve la lectura activa de la misma entrada; comprueba CSRF, contexto y `X-App-Entry`. `GET /sync-runs/{id}` informa estado; `POST /sync-runs/{id}/cancel` invalida la generación sin inventar una reversión remota. No hay reintento automático en bucle.

La lectura ocurre fuera de transacciones PostgreSQL. Hay dos trabajadores, sin cola ilimitada, plazo máximo de 30 s y descarte de resultados tardíos. El adaptador debe respetar también el deadline en sus llamadas de red: Python no puede detener a la fuerza un hilo bloqueado. Agotamiento devuelve espera, cuota conserva `Retry-After`, pérdida de permiso bloquea publicación, errores públicos son genéricos y no guardan cuerpos/credenciales del proveedor. Al reiniciar se marcan fallidas las lecturas interrumpidas. Cada publicación vuelve a comprobar permiso, identidad, sesión, entrada y generación.

Actualmente el reconciliador admite **inventario, monedas, FC Points y artículos sin asignar**. Los dos últimos son opcionales y cada uno exige cobertura explícita, valor observado y fecha de origen. Los artículos tienen ID único y tipo; el total nunca se deduce del número de jugadores. No certifica progreso remoto de Galería, DCP, objetivos, plantillas o Evos: el ejecutor rechaza cobertura que no pueda publicar. Esos módulos conservan registros locales y requieren un contrato adicional de progreso del proveedor. Una instantánea previa permanece intacta al fallar.

Cada copia observada incluye nombre/media/posición actuales; no se completan desde historia. Si omite atributos, posiciones alternativas, roles, PlayStyles, estrellas o puntos de Galería, esos detalles quedan vacíos/desconocidos en el estado actual. La instantánea histórica conserva la evidencia anterior; favoritos y notas locales se mantienen. Los indicadores críticos omitidos continúan como desconocidos y bloquean acciones incompatibles. No se presume un delta sin un protocolo documentado.

Esta implementación prueba el ciclo interno con datos sintéticos. No demuestra login EA, compatibilidad con la Community API, cobertura de un club real ni sincronización de progreso privado.

## Admisión por copia observada

La posesión observada no depende de las 22 variantes del catálogo documental ni de su vencimiento. `remote_evidence.py` comprueba en SQL, antes de paginar o contar, contexto verificado, snapshot/run publicado, identidad de variante y mapeo proveedor/copy_id. La evidencia solo la escribe el reconciliador interno. No hay un endpoint para subirla o marcar una copia como remota; la etiqueta `provider_verified` por sí sola es insuficiente.

Nombre, media y posición son obligatorios en cada lectura. Las etiquetas localizadas y evoluciones individuales conservan su variante y copy_id; el athlete_id evita alinear dos versiones del mismo futbolista. Metadatos omitidos no se heredan como hechos nuevos. `metadata_pending`, `ownership_source` y `observed_at` acompañan cada DTO. Los campos que exige un DCP deben estar conocidos tanto en el solver como en el validador; una propuesta de juego puede usar una copia cuyo estado de transferencia todavía sea desconocido.

Una lectura parcial o vencida conserva Mi club visible para inspección, pero no habilita cálculos dependientes de cobertura/vigencia. La ausencia completa se muestra como ausente, sin inventar venta o entrega; no se cuenta como disponible. El historial elegible de Galería conserva la observación aunque ya no haya una copia disponible. Las cesiones no se registran como adquisiciones y una Evo exige base conocida.

El formulario de una copia observada permite notas, favorito y precio local. Las rutas rechazan sustituir hechos observados por una edición manual. Los precios anotados no son cotizaciones de mercado. Las preferencias y sus candados permanecen separados de la evidencia del proveedor.
