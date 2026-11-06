# Fuentes y permisos · corte 5-nov-2026

Esta matriz registra evidencia y decisiones de implementación, no una autorización jurídica general. No existe adaptador de producción para leer una cuenta EA en este proyecto.

| Fuente | Evidencia contrastada | Decisión |
| --- | --- | --- |
| Web App/Companion EA | [Ayuda de acceso](https://help.ea.com/es/articles/ea-sports-fc/early-web-and-companion-app-start/), [reglas EA](https://help.ea.com/en/articles/ea-sports-fc/fc-rules/) | Enlace oficial e inicio manual. Captura visual local voluntaria, sin DOM, red autenticada ni control de EA en el nuevo flujo. No se afirma aprobación de EA al asistente. |
| FC Community API | [Anuncio del 27-jul-2026](https://www.ea.com/es/games/ea-sports-fc/news/pitch-notes-fc26-community-api-update) | Solo socios aprobados mencionados; este proyecto no figura. Adaptador desactivado, sin OAuth ficticio ni tokens de socios. |
| FUTBIN | [Términos, sección 13](https://www.futbin.com/tos), actualización publicada 24-feb-2026 | Prohíbe scraping/data mining no autorizado. Sin conector ni extracción automatizada. |
| FUT.GG | [/terms redirige a Stormstrike](https://stormstrike.gg/terms), 13-may-2026 | El uso automatizado requiere permiso expreso. Sin conector; su participación en Community API no transfiere derechos al proyecto. |
| FUTWIZ | Socio mencionado por EA; `/en/terms` y `/terms/` devolvieron 404 | Condiciones de reutilización no acreditadas. Sin conector; pendiente conseguir documentación/permisos adecuados. |
| Archivos/capturas del propietario | Selección explícita, contexto y revisión local | Importación legítima conforme a los derechos del propietario; no se infiere autorización de redistribución. Nunca se importa una sesión autenticada. |
| Fixtures propios | Generados en tests, sin datos de cuenta | Solo pruebas aisladas. Nunca declarar que representan un club EA real. |

No se consultan precios en tiempo real en este incremento. `services/providers.py` conserva el registro de adaptadores vacío en producción y los límites existentes. La sesión/cookie de Club Lab es **local**, distinta de una sesión EA. No se almacenan sesiones Playwright autenticadas, HAR ni credenciales; los tests abren únicamente la aplicación propia. [Advertencia oficial de Playwright sobre estado autenticado](https://playwright.dev/docs/auth).
