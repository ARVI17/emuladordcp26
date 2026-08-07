# Limitaciones conocidas

- La fórmula de media predeterminada y la química 0–3 son aproximaciones configurables, no reglas oficiales garantizadas de EA FC 26.
- El OCR depende de calidad, idioma, recorte y diseño de la captura; solo propone campos y exige revisión.
- No se incluyen precios de mercado en tiempo real ni fuentes externas; los valores se registran/importan manualmente.
- La recomendación automática de plantilla busca el mejor rating por puesto para 4-3-3 y no modela aún tácticas o estilos de juego avanzados.
- El formulario visual de creación de DCP expone los requisitos más usados; los requisitos avanzados están disponibles en la API documentada.
- Ollama se inicia con Docker, pero una instalación nueva todavía necesita ejecutar una vez `docker compose exec ollama ollama pull qwen2.5:3b`; el modelo queda persistido después.
- No hay autenticación multiusuario porque el alcance es un único usuario local. No debe exponerse directamente a Internet.
- La imagen E2E de Playwright incluye navegadores y por ello ocupa bastante más disco que las imágenes de producción; solo se construye al ejecutar el perfil de pruebas.
- El proyecto aporta el cliente y la interfaz ADB, pero no instala un emulador Android en el host. Debes iniciar uno o conectar un teléfono con ADB por TCP.
- La calibración ADB usa coordenadas absolutas: cualquier cambio de resolución, orientación, escala o diseño requiere recalibrar.
- La preparación busca y coloca jugadores por nombre; no resuelve automáticamente resultados ambiguos ni verifica cada carta con visión antes de pulsarla.
- Un plan marcado `completed` solo terminó la preparación. La entrega final queda siempre para confirmación humana y no se automatiza.

Estas limitaciones no afectan inventario persistente, protección, plantillas, objetivos, importación/exportación, simulación y entrega/restauración DCP ni funcionamiento sin Ollama o sin dispositivo ADB.
