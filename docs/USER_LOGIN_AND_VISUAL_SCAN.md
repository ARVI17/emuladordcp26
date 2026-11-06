# Iniciar sesión y escanear pantallas del club

El inicio de sesión pertenece a EA. Club Lab no pide contraseña, MFA, cookies ni tokens de EA. La [Web App oficial](https://www.ea.com/es-es/ea-sports-fc/ultimate-team/web-app/) se verificó desde la [ayuda de EA](https://help.ea.com/es/articles/ea-sports-fc/early-web-and-companion-app-start/) el 5-nov-2026.

1. Abre **http://localhost:8090**; tras la actualización usa Ctrl+F5 si ves la interfaz anterior. Entra en **Mi cuenta**. Crea un contexto de lectura asistida o selecciona el que ya corresponde a tu club. No mezcles cuentas en un contexto.
2. En **Escanear mi club**, pulsa **Abrir aplicación oficial de FC 27**. Inicia sesión y completa la verificación por tu cuenta. Abre una lista de jugadores antes de compartir.
3. Regresa a Club Lab, elige la sección y acepta el aviso de procesamiento visual local. Puedes configurar hasta cinco máscaras porcentuales, y una región de extracción. La detección de privacidad examina primero la pantalla recibida completa.
4. Pulsa **Compartir pestaña y comenzar escaneo**. Elige la pestaña o ventana del club en el selector del navegador. No selecciones correo, login, pagos, perfil ni escritorio completo.
5. Navega y desplázate manualmente en EA. Mantén cada grupo de cartas quieto unos segundos. El navegador espera dos muestras estables; solo hay una petición OCR simultánea. Usa vistas de lista con nombre, media y posición legibles; el reconocimiento de mosaicos gráficos complejos todavía no está contrastado.
6. **Pausar escaneo** libera las pistas y detiene el OCR. **Volver a compartir y reanudar** solicita permiso otra vez y continúa el lote. **Detener escaneo** termina la recepción y abre revisión. Salir a otra sección de Club Lab o cerrar su página también detiene la captura. Cancelar el selector nunca inicia otra captura automáticamente.
7. Revisa hasta 20 candidatas por página: nombre, media, posición, variante, propiedad y campos visibles. Selecciona expresamente las que quieres guardar. Los campos vacíos siguen desconocidos. Las coincidencias entre páginas son grupos provisionales: comprueba que sean la misma copia. Si son versiones distintas, excluye el grupo y utiliza lecturas manuales de sus fichas por separado. Dos copias simultáneas se mantienen como dos candidatas; no acreditan cantidad fuera de la vista.
8. Si ya existe una copia visual, selecciónala en **Correspondencia de copia**. Crear otra copia coincidente mantiene la ambigüedad y su exclusión del solver. Una coincidencia consumida o retirada no se reactiva desde este flujo.
9. Marca la revisión, escribe **GUARDAR SINCRONIZACION** y pulsa **Guardar sincronización**. Se guarda una transacción con snapshot anterior/posterior y diferencias. Repetir el mismo guardado devuelve el mismo snapshot. No se archivan cartas ausentes ni se modifica EA.

La cobertura permanece parcial/desconocida: recorrer una lista con filtros no prueba el contenido de las vistas ocultas. Se muestran páginas, candidatas únicas provisionales, posibles duplicados, descartes y fecha del último fotograma. El lote admite 50 páginas/1000 candidatas y caduca a los 30 minutos; revisa antes de que venza.

La alternativa **imagen de lista** procesa una captura proporcionada voluntariamente, con las mismas máscaras, revisión y límites. La lectura manual anterior sigue disponible para DCP, objetivos, principal y fichas. El escáner nuevo no necesita la extensión previa ni la instala.

## Privacidad y compatibilidad

Solo se comparte vídeo visual en memoria, sin audio ni grabación. El escáner envía PNG/JPEG/WebP a la API local, máximo 4 MB; no envía imágenes a Ollama ni a un proveedor externo. Tesseract recibe píxeles por stdin y devuelve TSV por stdout, sin archivos de imagen temporales. PostgreSQL conserva hechos estructurados, hashes, consentimiento, decisiones y snapshots, no píxeles ni texto OCR completo.

La detección de pantallas sensibles es heurística y puede fallar ante idiomas, diseños o texto ilegibles. No equivale a una garantía de anonimización. Una detección detiene las pistas y descarta el contenido de ese fotograma; volver a compartir requiere otro gesto. Las máscaras evitan transmitir las zonas elegidas. Cambiar resolución requiere revisar región/máscaras y empezar otro lote.

`getDisplayMedia` requiere contexto seguro y activación del usuario; [contrato del navegador](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getDisplayMedia). Se verifica la API antes de solicitar permiso. Las pruebas usan Chromium de escritorio y una pista sintética; en móvil se prueba el diseño y la cancelación, sin prometer captura nativa del navegador móvil. La compatibilidad con la pestaña personal y el layout real de FC27 permanece pendiente de prueba voluntaria del propietario.

## Después del inventario

La lectura manual permite revisar un DCP y simularlo con las cartas aptas desde **DCP observados**. Completa cesión, evolución, transferibilidad y cualquier metadato requerido; no se rellenan por inferencia. Se conservan titulares/candados/reservas. Este incremento no añade compras al solver ni certifica reglas oficiales: consulta [estado de implementación](IMPLEMENTATION_STATUS.md) antes de interpretar un coste como monedas a gastar.
