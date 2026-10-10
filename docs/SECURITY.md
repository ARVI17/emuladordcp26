# Seguridad local

## Edición FC27, revisión y transacciones

- El inventario y sus consumos se separan por edición. La migración conserva FC26 y activa FC27 sin copiar cartas.
- La protección manual y la protección de cualquier plantilla se acumulan. Desproteger un equipo no elimina los demás candados.
- Confirmación y restauración reservan el inventario, recargan su estado y verifican el propietario de cada consumo. Repetir IDs o restaurar consumos ambiguos se rechaza antes de mutar.
- CSV/XLSX requieren vista previa vinculada al archivo y edición mediante HMAC, con expiración y recibo idempotente. Las fórmulas se neutralizan en la exportación; los metadatos estructurados se validan como datos.
- La clave privada de revisión y los recibos internos no se devuelven ni editan por el endpoint de settings.
- Los paquetes de contenido se validan y confirman por hash. Una repetición antigua ya recibida no vuelve a escribir definiciones más recientes.
- Las noticias solo leen fuentes públicas fijas de EA, sin redirecciones ni sesión de cuenta y con límite de bytes/tiempo. La URL de procedencia de un paquete es informativa: no se descarga.
- Las puntuaciones y reglas incompletas se marcan pendientes; Galería/evoluciones no alteran datos en EA ni acreditan recompensas.
- Las reservas de dispositivo cubren planes, capturas, scans y entradas manuales. Un worker antiguo no puede reactivar un plan cancelado; el arranque cancela operaciones huérfanas.
- OCR limita bytes, píxeles, tiempo y concurrencia. XML temporal y códigos de emparejamiento se eliminan o redactan incluso cuando falla la operación.

## Controles de la instalación

- No existen OAuth, credenciales ni sesiones de EA.
- Pydantic/Zod validan tamaños, rangos y campos; SQLAlchemy parametriza consultas.
- CORS acepta únicamente orígenes configurados y Nginx añade CSP, `nosniff`, `SAMEORIGIN` y política de referente.
- Cargas limitadas por Nginx y backend; OCR acepta solo JPEG, PNG y WebP. CSV/XLSX requieren extensión y esquema válidos.
- Las capturas se procesan en memoria y no se guardan automáticamente.
- Las lecturas de inventario persisten únicamente hashes/firmas SHA-256, candidatos revisables y progreso. La jerarquía de accesibilidad se limita a 2 MB, solo se acepta en `Futb. de Mi Club`, se elimina del dispositivo y no se devuelve ni persiste.
- Importar candidatos exige `IMPORTAR <id>`; archivar los nombres demo exige la frase distinta `REEMPLAZAR DEMO <id>`.
- ADB solo acepta direcciones/seriales validados y un conjunto restringido de pulsación, deslizamiento, texto seguro, teclas, espera, captura y lectura temporal de UI. El avance de inventario valida pantalla, resolución, zona del botón y cambio de cartas antes de guardar progreso.
- El código temporal de `adb pair` debe tener seis dígitos, viaja solo a través de la API local y nunca se persiste ni aparece en auditoría.
- Los planes ADB se generan desde una solución revalidada, exigen la frase `PREPARAR <id>`, pueden cancelarse y nunca contienen el botón de entrega final.
- Las excepciones internas se registran localmente y el frontend recibe un mensaje genérico.
- Acciones críticas generan auditoría: cambios, protección, importación, entregas, restauraciones y chat.
- `.env`, respaldos, cargas y artefactos se excluyen de Git.

El sistema no incluye autenticación multiusuario y debe permanecer en una máquina o LAN confiable. Si se publica mediante otro proxy, añade TLS, autenticación y reglas de firewall. Cambia la contraseña demostrativa de PostgreSQL antes de cualquier exposición de red.

Los scripts de restauración solo aceptan dumps dentro de `backups`, crean una copia previa y no eliminan esa copia automáticamente.

El dispositivo conserva su propia sesión. El sistema no pide ni almacena usuario, contraseña, cookie, token ni código de verificación. ADB concede control al propietario del equipo: no expongas su puerto fuera de la máquina/LAN confiable, revisa la captura antes de autorizar y desactívalo cuando termines. Un cambio de resolución o pantalla invalida en la práctica la calibración aunque sus valores sigan guardados.

OCR no constituye verificación de identidad de una carta ni de un requisito. Ningún candidato se convierte en jugador hasta que el usuario corrige los campos, lo selecciona y escribe la frase requerida. La lectura de DCP solo crea un borrador local y no actúa sobre Companion.


## Dependencias en la revisión FC27

La revisión actualiza FastAPI/Starlette, multipart, Pillow y las herramientas frontend afectadas, fija un lockfile reproducible y ejecuta auditoría npm de producción. El resultado local de producción fue cero avisos. El árbol completo de desarrollo conserva cinco entradas altas por un mismo aviso de `braces` en la cadena de Tailwind 3: [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm). No se presenta ese árbol como libre de vulnerabilidades; resolver la dependencia requiere revisar el cambio del pipeline de CSS o una versión corregida de su dependencia. El resultado debe consultarse de nuevo cuando cambien las versiones.
