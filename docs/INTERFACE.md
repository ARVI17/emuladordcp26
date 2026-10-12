# Interfaz personal FC27

La SPA usa componentes propios y la descripción de la portada aportada por el usuario: cabecera oscura, barra lateral, panel de artículos sin asignar y tarjetas azul/turquesa. No se descargó código privado ni se acreditó acceso a las páginas interiores de EA. El aviso «Asistente no oficial de FC27» permanece visible.

`lib/navigation.ts` centraliza secciones y hash routes. La ruta conserva la sección al recargar y permite Atrás/Adelante; se retoma únicamente el modo que ya consta en la sesión local del servidor. Una sesión nueva abre Inicio con cuenta sin vincular. Un módulo sin cobertura muestra su motivo y acceso a Mi cuenta. Plantillas separa Principal, Recomendadas y Para objetivos; Asistente agrupa análisis, fichajes, planes, práctica, referencias e IA. El menú móvil usa un diálogo nativo con Escape y devolución del foco.

`AccountHeader` y `HomePage` usan `/dashboard.account`: el perfil manual no rellena identidad ni saldos remotos. Los recursos ausentes indican «Sin consultar». La tarjeta de tienda conduce al acceso oficial externo y explica que no hay lectura de ofertas. Las tarjetas y pestañas tienen navegación funcional.

`ContextHelp` usa la sección, entrada/snapshot y selección actual (IDs, formación, segmento u objetivos). Su orientación es determinista y consulta la protección de la principal al abrirse, sin solicitudes a Ollama ni mutaciones. Los cálculos siguen en sus motores correspondientes. Cerrar el panel no pierde el trabajo de la pantalla.

`lib/i18n.ts` concentra términos, estados, validación Zod y formatos `es-CO`. La zona inicial es `America/Bogota`, configurable en Ajustes; los instantes viajan en UTC. Las preferencias de presentación se conservan en este navegador. CSV/XLSX reconocen separadores de miles ingleses/colombianos en importes enteros y rechazan fracciones o agrupaciones ambiguas.

La versión desplegada se acredita mediante `/build.json` y `/api/build`, no por la apariencia. Las capturas de prueba se guardan localmente en `frontend/test-results/`; abrir una captura no mantiene otro servidor en ejecución.
