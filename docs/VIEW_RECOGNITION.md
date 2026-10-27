# Reconocimiento e ingesta por dominios · extensión 0.4.0

Conserva WXT/MV3 y el inspector privado. Conecta **perfil → observación fragmentada → recibo PostgreSQL → revisión en Club Lab → inventario/requisitos → cálculo existente**. Las pruebas usan datos sintéticos. **No se ha contrastado un perfil ni una propuesta con el club personal.**

## Versiones y destino

Comprobado el 27-oct-2026: `http://localhost:8090` sirve frontend/API `ad73edf14bcafa827648f4dc70a4ea7f20e52ad6`, migración `0018`, cinco servicios saludables y volumen `emuladordcp26_postgres_data`. No se pudo inspeccionar la extensión del navegador personal ni existe conexión de depuración Chrome/Edge. El código nuevo requiere **0019**. El inspector funciona sin backend y se conservan contrato/recibos v1.

Un push no despliega. V2 se rechaza ante un backend antiguo sin buscar otro puerto. Actualizar el principal requiere autorización concreta, respaldo restaurado aparte e imágenes de recuperación según la solicitud y [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md).

## Recorrido preparado

1. `python scripts/package_reader.py state/sprints/<proyecto>/result.json` extrae la extensión de una imagen Docker probada. Produce ZIP/hash y carpeta `chrome-mv3` en `state/reader-package-*/`, sin datos personales.
2. Cargar la carpeta en `chrome://extensions`. Para conservar el ID/almacenamiento existente, reemplazar el contenido de su carpeta y recargar. Un ID nuevo debe emparejarse otra vez.
3. **Abrir FC27 oficial**, iniciar sesión personalmente en EA y conceder `activeTab` mediante el icono de la extensión. Contraseña/MFA y sesión permanecen en EA.
4. Seleccionar texto de una región y reconocerla. Reutilizar mapas existentes o crear la definición; asignar visualmente contenedor de registro y textos/etiquetas para los campos. El JSON queda como opción avanzada.
5. **Probar definición en mapa guardado** prueba la evidencia privada sin acreditar EA. Sigue disponible la muestra propia. Contrastar una vista previa nueva en la pestaña real y activar. Editar invalida pruebas; `bounded-region-2` invalida pruebas antiguas, conservando mapas/definiciones.
6. Elegir un contexto asistido en Mi cuenta y emparejar la extensión con código temporal. Confirmar que sigue siendo el club de esa pestaña y **Leer y enviar observación a Club Lab**. Si cambió de cuenta, crear otro contexto: un nombre no verifica identidad.
7. Actualizar las observaciones recibidas, revisar los campos y admitir por lote. Se muestran 20 filas por página y evidencia completa por fragmento. No se admiten observaciones incompletas.
8. **Registrar mi principal** sigue siendo explícito: once, banquillo y reservas conocidos. Leer no activa ni sobrescribe plantillas. DCP/objetivos quedan como texto pendiente; revisar todos los comparadores/condiciones en su editor y usar las pantallas de cálculo existentes. La principal incompleta se muestra como carencia de seguridad.

## Contrato, cobertura y recuperación

OpenAPI documenta v1/v2 de `/reader/events`. V2 separa cuenta, inventario, ficha, plantilla, DCP, objetivos y Galería; conserva perfil/revisión/hash/origen/ruta/idioma, contexto derivado del emparejamiento, documento, flujo/secuencia, fechas, ámbito y manifiesto. `source_updated_at` es nulo: una lectura DOM no prueba actualización remota. El servidor registra `received_at`. Muestras/exportaciones/páginas observadas mantienen procedencia distinta y `provider_verified=false`.

Límites: 300 registros por región; 30 y 128 KB por fragmento; 4.000 nodos visitados, 1.200 incluidos, profundidad siete y 512 KB por mapa; cola de 100 fragmentos / 2 MB; revisión en 30 minutos. Son límites de región/transporte, no del club. Saturación y omisiones son visibles; no se recortan filas para aparentar cobertura completa. Imágenes, canvas, shadow DOM y formularios quedan excluidos. Texto legible hasta 5.000 caracteres; los mayores quedan desconocidos.

La firma ignora contenido privado y multiplicidad de subárboles idénticos: 65 y 10 filas compatibles comparten perfil. Cada campo sigue exigiendo unicidad dentro del registro. Carga, idioma distinto, duplicados ambiguos, ámbitos solapados o estructura nueva bloquean lectura. ES/EN normalizan posiciones y separadores de miles: `000,000` queda desconocido; `0` puede ser válido.

Recibos/manifiesto se confirman atómicamente. Un reenvío conserva ID/contenido/fecha y otro contenido con el mismo ID se rechaza. Se aceptan fragmentos desordenados, sin admitir faltantes. Los recibos originales son inmutables; el resumen informa el estado actual. La cola sobrevive al reinicio del worker. El checkpoint registra recepción, espera del usuario o pausa/motivo. Pausar conserva historial/cola; reintentar no navega. No se promete entrega distribuida exactamente una vez.

La admisión reutiliza correspondencias únicas revisadas y conserva preferencias/protecciones. Identidades ambiguas, datos contradictorios, retiradas u observaciones antiguas quedan pendientes; no se multiplican ni reactivan copias. Filas simultáneas pueden demostrar multiplicidad mínima, nunca IDs EA. Galería conserva evidencia separada sin certificar historial, conjuntos ni recompensas.

## Capacidades y pendientes

Las [normas EA](https://help.ea.com/es/articles/ea-sports-fc/fc-rules/) y [API comunitaria](https://help.ea.com/es/articles/ea-sports-fc/community-api/) se consultaron el 27-oct-2026. Permiso del navegador no significa aprobación EA; las capacidades de socios no se trasladan a Club Lab. Hay inspección guiada, extracción manual con perfil y recepción local revisable; no navegación externa autónoma, sincronización de proveedor ni escritura remota. Este recorrido no utiliza OCR/LLM.

[Birmingham público](https://www.fut.gg/fut-gallery/premier-league/birmingham-city/), revisado el 27-oct-2026, identifica FC27 y 15 futbolistas del Birmingham City femenino. Sus cantidades de ejemplo/selección/progreso no pertenecen al usuario. Importación específica y planificación económica quedan para H4; no se inventaron precios, reglas ni progreso personal.

Pendientes: cargar/autorizar extensión y contrastar una propuesta con datos personales; despliegue autorizado; actualización automática tras confianza inicial; detección de cuenta más allá de confirmación humana; recorridos entre páginas y conciliación remota. El checkpoint reanuda transporte manual, no un recorrido autónomo por el club. [Pruebas](TESTING.md).

Se mantuvo la arquitectura. Zod 4.6.7 (MIT) corrige [GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5); `@hookform/resolvers` 5.2.2 (MIT) adapta el formulario existente. Lockfiles y validadores se actualizaron juntos; no se añadió otro parser, extensión o servicio.