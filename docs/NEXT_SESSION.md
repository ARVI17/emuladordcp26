# Continuación exacta · Club Lab FC27

Corte **16 de noviembre de 2026**. Prioridad: **plantilla competitiva con las cartas reales del propietario**. DCP, monedas, compras, Galería y Evos sirven a ese objetivo. La entrega de continuidad no completa el producto.

## Leer y comprobar al retomar

1. AGENTS.md, [estado y criterios](PROJECT_STATUS.md), [prompt maestro](MASTER_PROMPT.md), [auditoría actual](AUDIT_20261116.md) y código/pruebas de la capa elegida.
2. Revisar git status --short, rama, worktrees y PR. Checkout: C:/Users/arvi_/emuladordcp26; rama codex/continuidad-club-competitivo-20261116, base 4ed6d48 de agent/visual-capture-fc27-20261105 / PR #8. Conservar la eliminación ajena de .vscode/settings.json. No tocar el worktree emuladordcp26-fc27-planificador (34c4e05).
3. Ejecutar python scripts/project_status.py o powershell -File scripts/fc27.ps1 Memoria. Leer state/continuity/latest.md: fecha, HEAD, dirty, servicios, SHA servido y SHA/alcance de pruebas. No usar un informe antiguo para acreditar el estado actual.
4. La fuente editable es PROJECT_STATE.json. Al cerrar actualizar hitos/fecha, ejecutar --render-plan y --check, y actualizar esta nota y TESTING. fc27.ps1 y el cierre del verificador regeneran el diagnóstico; no cambian por sí mismos la aceptación funcional ni trabajan entre sesiones.

## Instalación personal acreditada

- Única instalación Compose: emuladordcp26, **http://localhost:8090**. Los cinco servicios estaban detenidos al comenzar; se arrancaron por los mismos IDs y quedaron saludables.
- Frontend/API: **8a808605d27dabc43266fdc4feeb739789708e5f**, esquema **0021**, construcción local limpia. El código de aplicación coincide con esta rama; este sprint modifica memoria, diagnóstico, CI y documentación. No requiere nuevo despliegue ni migración.
- Consulta READ ONLY del 16-nov: **132 jugadores históricos FC26 retirados, cero cartas activas FC27, cero snapshots visuales**. Sin borrado ni reconversión de inventario.
- Volúmenes: emuladordcp26_postgres_data y emuladordcp26_ollama_data. PostgreSQL en **127.0.0.1:54326** por reserva de Windows sobre 55432; Nginx loopback 8090.
- Composición privada fijada: state/visual-scan-release/release.compose.json; recuperación: original.compose.json, imágenes anteriores y backups/visual-scan-before-20261105.dump. Ese respaldo es histórico: obtener/restaurar uno nuevo antes de actualizar datos.
- fc27.ps1 Inicio|Estado|Parada reutiliza contenedores. No usar Compose de un checkout viejo ni volver a 0005. No dejar otra aplicación permanente en 8081.

## Próximo sprint: KNOW-1 y DATA-1 antes de TEAM-1

**Bloqueo actual confirmado:** formaciones y 29 referencias documentadas vencieron el 10-nov; el paquete de contenido también venció. La suite integral actual detecta los bloqueos. Primero contrastar fuentes/posiciones de las formaciones necesarias, conservar evidencia y actualizar su revisión explícita. No alargar fechas para hacer pasar tests. Separar pruebas históricas con reloj controlado de la regresión de caducidad real. El diagnóstico muestra el recuento vigente/vencido/pendiente del checkout; consultar TESTING para las dos reproducciones.

1. **Aceptar el club real**: el propietario abre la Web App oficial y comparte voluntariamente una vista de juego. Contrastar 20 cartas, corregir dos y reescanear. Incluir once y siete suplentes. No solicitar credenciales ni iniciar captura/login por cuenta del usuario.
2. **Resolver identidad**: comprobar variantes y copias legítimas, especialmente entre páginas. El extractor actual reconoce filas legibles sintéticas; no está contrastado con fichas gráficas EA. Si falla esa vista, medir segmentación/OCR con una muestra permitida, mejorar y repetir dos veces la regresión. Confianza textual no acredita identidad. Imágenes personales fuera de Git.
3. **Proteger y comparar**: selección explícita de principal, banquillo y reservas; alternativas propias por posición/atributos. No inventar química oficial ni prometer victorias. Guardar una alternativa conserva principal y datos EA.

Si no hay una vista real disponible, avanzar en extractor/reconciliación con pruebas sintéticas permitidas y mantener la aceptación personal pendiente. No convertir fixtures en club real para cerrar el hito.

## Dependencias siguientes concretas

- services/contexts.py:require_module permite squads/analysis/chat/gallery en modo visual, pero bloquea market/transfers y consumos genéricos. Diseñar evidencia revisada y presupuesto declarado para **simulaciones**; no suprimir esa guarda.
- services/providers.py:ADAPTERS sigue vacío. La Community API de otros sitios no autoriza este proyecto. Precios manuales/importados permitidos ofrecen una vía sin scraping EA.
- DCP: tradicional y Streamlined reales, fuente/fecha/expiración y prueba independiente; después compras externas, presupuesto, oportunidad y optimalidad. _cost conserva los coeficientes efectivos; AppSetting es informativo.
- Ventas: copias prescindibles/transferibles, protecciones y compromisos intactos, perjuicio deportivo y reposición. Una venta pendiente nunca financia una compra.
- Galería: conjunto real, historial, premios reclamados, reglas/puntos y precios. Rutas locales existentes no acreditan la solución personal.
- Mantener los criterios de [PROJECT_STATUS](PROJECT_STATUS.md). No reiniciar una auditoría general mientras estos hechos sigan acreditados.

## Verificación y entrega

    python -m unittest discover -s scripts/tests -v
    python scripts/project_status.py --check
    python scripts/verify_docker.py --scope full --subnet 10.231.27.0/24 --build-environment local

El verificador rechaza solapamiento, usa tmpfs y conserva principal/volúmenes. Elegir otra /24 privada libre si hace falta, sin borrar redes ajenas. Resultados nuevos en [TESTING](TESTING.md); historia en [IMPLEMENTATION_STATUS](IMPLEMENTATION_STATUS.md).

**Resultados de este sprint:** 23 pruebas de herramientas pasan (14 nuevas). Integral acb4979c15: 251 Pytest pasan / 68 fallan; repetición focalizada 65a7a5d1b1: 4 pasan / 8 fallan. Causas de caducidad en TESTING; no hay pase integral actual. Build/arranque/health/OpenAPI/Alembic/limpieza pasan y principal/volúmenes siguen iguales. Ambos ensayos sobre base 4ed6d48 con cambios locales, no atribuirlos a un commit posterior. No se ejecutaron Vitest/Playwright/extensión porque el verificador paró en Pytest.

El pase histórico dc69595a37 sobre 8a80860 fue 319 Pytest, 42 Vitest, 39 Playwright y 14 extensión; canvas móvil omitido. No es estado verde actual. No se probó cuenta EA personal, selector nativo real, Safari, ADB físico o inferencia GPU.

Código → pruebas pertinentes → Docker aislado → diff/secretos → commit → push/SHA remoto → PR en borrador. Sin merge automático. Registrar fallos, repeticiones, omisiones, SHA probado/servido y cambios ajenos. Despliegue futuro: permiso aplicable, respaldo reciente restaurado y recuperación preparada.
