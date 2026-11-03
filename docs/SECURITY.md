# Seguridad local

- No existen OAuth, credenciales ni sesiones de EA.
- Pydantic/Zod validan tamaños, rangos y campos; SQLAlchemy parametriza consultas.
- CORS acepta únicamente orígenes configurados y Nginx añade CSP, `nosniff`, `SAMEORIGIN` y política de referente.
- Cargas limitadas por Nginx y backend; OCR acepta solo JPEG, PNG y WebP. CSV/XLSX requieren extensión y esquema válidos.
- Las capturas se procesan en memoria y no se guardan automáticamente.
- Las lecturas de inventario persisten únicamente hashes/firmas SHA-256, candidatos revisables y progreso. La jerarquía de accesibilidad se limita a 2 MB, solo se acepta en `Futb. de Mi Club`, se elimina del dispositivo y no se devuelve ni persiste.
- La observación ligera `/emulator/scans/{id}/observe` solo se ejecuta por una pulsación explícita del usuario. No tiene sondeo automático, no toma capturas, no usa OCR/Ollama, no envía pulsaciones y no modifica la sesión en otras pantallas o ante una firma repetida.
- La carga completa exige `IMPORTAR TODO EL CLUB`, se limita a 5000 pendientes y deduplica nombre+media+posición contra cartas activas y eliminadas. Las incompletas permanecen pendientes; los campos no visibles quedan marcados como no disponibles.
- Importar candidatos exige `IMPORTAR <id>`; archivar los nombres demo exige la frase distinta `REEMPLAZAR DEMO <id>`.
- ADB solo acepta direcciones/seriales validados y un conjunto restringido de pulsación, deslizamiento, texto seguro, teclas, espera, captura y lectura temporal de UI. El avance de inventario valida pantalla, resolución, zona del botón y cambio de cartas antes de guardar progreso.
- El código temporal de `adb pair` debe tener seis dígitos, viaja solo a través de la API local y nunca se persiste ni aparece en auditoría.
- Los planes ADB se generan desde una solución revalidada, exigen la frase `PREPARAR <id>`, pueden cancelarse y nunca contienen el botón de entrega final.
- El análisis guiado `/ai/dcp/analyze` es una simulación determinista sin escrituras, excluye protegidos y puede excluir titulares. La SPA exige `CREAR PLAN <segmento>` antes de solicitar un borrador; no ofrece entrega desde IA.
- Guardar un DCP visible exige `ACTUALIZAR DCP`; guardar objetivos visibles exige `ACTUALIZAR OBJETIVOS`. Ambos son borradores revisados y nunca eliminan automáticamente entradas ausentes.
- Las excepciones internas se registran localmente y el frontend recibe un mensaje genérico.
- Acciones críticas generan auditoría: cambios, protección, importación, entregas, restauraciones y chat.
- `.env`, respaldos, cargas y artefactos se excluyen de Git.

El sistema no incluye autenticación multiusuario y debe permanecer en una máquina o LAN confiable. Si se publica mediante otro proxy, añade TLS, autenticación y reglas de firewall. Cambia la contraseña demostrativa de PostgreSQL antes de cualquier exposición de red.

Los scripts de restauración solo aceptan dumps dentro de `backups`, crean una copia previa y no eliminan esa copia automáticamente.

El dispositivo conserva su propia sesión. El sistema no pide ni almacena usuario, contraseña, cookie, token ni código de verificación. ADB concede control al propietario del equipo: no expongas su puerto fuera de la máquina/LAN confiable, revisa la captura antes de autorizar y desactívalo cuando termines. Un cambio de resolución o pantalla invalida en la práctica la calibración aunque sus valores sigan guardados.

OCR no constituye verificación de identidad de una carta ni de un requisito. Ningún candidato se convierte en jugador hasta que el usuario corrige los campos, lo selecciona y escribe la frase requerida. La lectura de DCP solo crea un borrador local y no actúa sobre Companion.
