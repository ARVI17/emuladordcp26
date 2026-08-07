# Seguridad local

- No existen OAuth, credenciales ni sesiones de EA.
- Pydantic/Zod validan tamaños, rangos y campos; SQLAlchemy parametriza consultas.
- CORS acepta únicamente orígenes configurados y Nginx añade CSP, `nosniff`, `SAMEORIGIN` y política de referente.
- Cargas limitadas por Nginx y backend; OCR acepta solo JPEG, PNG y WebP. CSV/XLSX requieren extensión y esquema válidos.
- Las capturas se procesan en memoria y no se guardan automáticamente.
- ADB solo acepta direcciones/seriales validados y un conjunto restringido de pulsación, deslizamiento, texto seguro, teclas, espera y captura.
- Los planes ADB se generan desde una solución revalidada, exigen la frase `PREPARAR <id>`, pueden cancelarse y nunca contienen el botón de entrega final.
- Las excepciones internas se registran localmente y el frontend recibe un mensaje genérico.
- Acciones críticas generan auditoría: cambios, protección, importación, entregas, restauraciones y chat.
- `.env`, respaldos, cargas y artefactos se excluyen de Git.

El sistema no incluye autenticación multiusuario y debe permanecer en una máquina o LAN confiable. Si se publica mediante otro proxy, añade TLS, autenticación y reglas de firewall. Cambia la contraseña demostrativa de PostgreSQL antes de cualquier exposición de red.

Los scripts de restauración solo aceptan dumps dentro de `backups`, crean una copia previa y no eliminan esa copia automáticamente.

El dispositivo conserva su propia sesión. El sistema no pide ni almacena usuario, contraseña, cookie, token ni código de verificación. ADB concede control al propietario del equipo: no expongas su puerto fuera de la máquina/LAN confiable, revisa la captura antes de autorizar y desactívalo cuando termines. Un cambio de resolución o pantalla invalida en la práctica la calibración aunque sus valores sigan guardados.
