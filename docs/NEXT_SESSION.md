# Continuación exacta · Club Lab FC27

Corte **17-nov-2026 · WXT 0.7.0**. Aplicación **abb7e6e8b46c3ca7328856076ff472efee078e56/0023 servida en 8090**, cinco servicios saludables. Recorrido por páginas en segundo plano implementado y probado; **instalación WXT y aceptación personal pendientes**. El objetivo es abrir la app y actualizar desde EA sin capturas/transcripción ni navegación manual. [Contrato](AUTOMATIC_CLUB_SYNC.md), [estado generado](PROJECT_STATUS.md), [fallos y pruebas](TESTING.md).

## Siguiente acción concreta

1. Comprobar `python scripts/project_status.py`; no reconstruir/repetir suites si no cambió código. En Chrome, el propietario debe cargar una sola vez `C:/Users/arvi_/ClubLab-Lector-0.7/chrome-mv3` desde Cargar descomprimida. Guía corta `C:/Users/arvi_/ClubLab-Lector-0.7/INSTALAR.txt`. Es el artefacto exacto probado, también conservado en `state/wxt-background-release-20261117/` con hashes. No instalar 0.5/0.6 ni confundir la extensión oficial de ChatGPT con este lector. `chrome://extensions` está bloqueado al agente: no eludir mediante Selenium/CDP/perfil.
2. Recuperar control de la pestaña oficial si procede: la última vista leída mostró Login y después dos intentos de control agotaron el plazo. No afirmar que EA está autenticada. Login/MFA por el propietario en EA; ninguna plataforma externa, cookie o contraseña en Club Lab.
3. Volver a la pestaña habitual de Club Lab (`http://localhost:8090/#/cuenta`), conservar su origen y el contexto de las veinte copias previas; activar una sola vez. No abrir otro contexto por cambiar localhost a 127.0.0.1. La lectura debe comprobar plantilla y recorrer páginas. Contrastar controles reales de paginación; lista, biografía y plantilla EN se observaron en el sprint previo, varias páginas/ES siguen probadas solo con fixtures.
4. Abrir la app dos veces: tres recibos nuevos contando la carga inicial, sin clics rutinarios en EA, IDs conservados, once/siete suplentes y reservas observadas protegidos. La principal puede añadir copias ajenas a las primeras veinte; no confundir total mayor con duplicación. El helper privado `state/real-auto-first20-20261117/verify.py` sigue **sin ejecutar**; requiere recibos reales. Ya agrupa lotes por recibo v2, exige tres publicaciones completas, conserva las veinte copias previas y compara el inventario paginado entero; valida el último final de recorrido, candados y 132 históricos. No confundir tres lotes con tres aperturas. No copiar inventario/secretos a memoria.
5. Conectar cada recibo WXT con el informe calculado de recomendaciones y retirar instrucciones manuales del recorrido habitual. Hoy `invalidateClub` refresca la vista Análisis, pero `ClubAnalysis` usa un workflow separado que aún requiere iniciar Analizar mi club; no declararlo automático. Después de aceptación, consultar DCP vigentes y ofertas del mercado PS5 con lectores propios contrastados, para recomendar composiciones y ventas/compras; Galería requiere sus reglas/variantes acreditadas. No ampliar formularios manuales ni ejecutar compras, ventas o entrega final.

## Implementación y límites

WXT 0.7 abre EA inactiva si no hay pestaña, lee plantilla y páginas y publica atómicamente. El progreso y los datos temporales quedan en `chrome.storage.session` entre eventos del worker; `chrome.alarms` reanuda una etapa si el proceso se detuvo antes de enviarla, revalidando permisos y sin duplicar clics; Chrome debe seguir abierto. Límite 50 páginas/1000 cartas/30 minutos y dos minutos por etapa. No renueva sesión EA, no trabaja con Chrome cerrado ni garantiza reanudación tras perder el documento. Se detiene por interacción del propietario, cambio de club, controles desconocidos, repetición de página o error.

Conciliación conservadora: no fusiona copias indistinguibles, no retira por ausencia parcial ni resucita consumidas. Final de búsqueda no acredita inventario completo. Nombre del club y firma visual no son identidad universal ni ID EA; `provider_verified=false`. Las reglas EA restringen automatizaciones no autorizadas; no prometer riesgo cero. Mercado, DCP y Galería no se obtienen por paginar jugadores.

## Evidencia y versión

WXT corregido **d9c02129fd** (f6b77b9 limpio): 18 aprobados. Integral limpio **9aab1129ae** (abb7e6e): **374 Pytest, 43 Vitest, 41 Playwright, 18 WXT**; un canvas móvil omitido. Veinte EN/ES y 65 en cuatro páginas ejecutan carga y dos reaperturas, conservan IDs/18 candados. Caso 65 incluye creación inactiva y terminación del worker; integral añade renderizado inicial demorado. Lector final **6fbee4dd8d1e6558506d869d1898d7ca114c1023**, pase **7675740d85**: 18 aprobados con interrupción deliberada antes de la siguiente orden y recuperación por alarma; backend/frontend/Nginx idénticos a abb7e6e. Datos sintéticos; no aceptación personal. Herramientas: 23 aprobadas.

Las veinte cartas personales anteriores y 132 históricos permanecen intactos. Su procedencia sigue siendo texto visible revisado (`user_reviewed_text`), sin recibos automáticos ni candados personales acreditados. No reutilizar la aceptación manual como prueba automática.

[CI final del lector 6fbee4d](https://github.com/ARVI17/emuladordcp26/actions/runs/44181922329): backend, frontend, extensión y continuidad aprobados. La instalación inicial se solicitó al propietario; al cierre no había respuesta que acreditara su carga. No repetir la misma pregunta sin revisar mensajes nuevos.

## Recuperación

En `C:/Users/arvi_/emuladordcp26`, respaldo `backups/background-before-20261117.dump` restaurado en `fc27_background_20261117`: **47 tablas y 152 registros idénticos**. Alembic 0023 ensayado sin cambios de esquema. Evidencias y composiciones en `state/background-release-20261117/`; `rollback.compose.json` conserva imágenes 988bbbd. No restaurar sobre la base personal para probar.

Se recrearon backend/frontend/Nginx con las imágenes exactas verificadas y configuración Nginx privada. Database/Ollama conservaron identidad/arranque y volúmenes intactos. DNS dinámico corrige el 502 causado por una IP antigua de backend. Composición canónica `state/visual-scan-release/release.compose.json` apunta a este despliegue. Solo loopback 8090/54326; no segunda app permanente.

Trabajo: `C:/Users/arvi_/.codex/worktrees/fc27-source-review-verification/emuladordcp26`, rama `codex/wxt-first20-20261116`, [PR #11 en borrador](https://github.com/ARVI17/emuladordcp26/pull/11), sin merge. Conservar cambio ajeno `.vscode/settings.json` del checkout original. HEAD puede avanzar por memoria: distinguirlo de SHA servido.

Operación: `powershell -ExecutionPolicy Bypass -File scripts/fc27.ps1 Estado`; memoria: editar PROJECT_STATE, `python scripts/project_status.py --render-plan` y `--check`. No existe agente que actualice por sí solo el juicio funcional. Historial de cortes y fallos en TESTING/CHANGELOG_DETAILED.
