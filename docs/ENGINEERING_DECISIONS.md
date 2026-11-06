# Decisiones de ingeniería · escaneo 2026-11-05

1. **Base concordante con la instalación.** El checkout inicial 0005 no coincide con la base personal 0019. Se parte de la evolución existente 34c4e05/0020 en una rama nueva. No se mezcla main ni se reemplaza el proyecto. [Auditoría](AUDIT_20261105.md).
2. **Captura en el host por el navegador.** getDisplayMedia, vídeo/canvas en memoria y permiso por gesto. El backend Linux no intenta capturar el escritorio Windows. No se instala extensión ni ayudante nativo para este recorrido.
3. **Una cola de tamaño uno.** Muestreo cada 1,2 s después de terminar la petición previa, dos muestras estables, comparación por bloques de una miniatura 160×90, pausa/stop mediante generaciones y cancelación real de Tesseract. Los umbrales 1,5/2 son tolerancias de píxeles ensayadas sintéticamente; no umbrales de precisión OCR ni garantía sobre animaciones EA.
4. **Tesseract existente por tuberías.** OpenCV normaliza contraste/escala; Tesseract devuelve TSV y confianza de palabras. El cuerpo HTTP binario evita el spool de multipart. No dependencias nuevas de OCR, GPU ni modelo LLM. Se prioriza lista legible y ROI manual, con limitación explícita en mosaicos complejos.
5. **Conservar incertidumbre y datos anteriores.** Las candidatas no se admiten por confianza. Revisión explícita, correspondencia de copias, bloqueos de consumo y snapshot atómico; nunca archivar ausentes de una sesión parcial. Los estados de cobertura verificada quedan reservados.
6. **Red de pruebas aislada.** `verify_docker.py --subnet` admite /24 privada libre y rechaza solapamientos Docker. Necesario porque este motor agotó sus pools automáticos. No cambia ni borra redes/volúmenes ajenos.

## Dependencias contrastadas

Versiones observadas dentro de la imagen de prueba, no afirmación de «última versión estable». Licencias de metadatos instalados; el repositorio conserva sus ficheros/licencias originales.

| Biblioteca | Versión/licencia observada | Problema y compatibilidad | Consumo/alternativa/decisión |
| --- | --- | --- | --- |
| FastAPI / Pydantic | 0.143.0 MIT / 2.11.3 MIT | API tipada en Docker Linux, navegador Windows | Reutilizadas; sin servicio nuevo |
| SQLAlchemy / Alembic | 2.0.40 MIT / 1.15.2 MIT | Transacción y esquema PostgreSQL | Reutilizadas; migración aditiva |
| PostgreSQL | 16-alpine, licencia PostgreSQL | Datos privados persistentes | Prueba aislada: ~92 MiB en una muestra en reposo; no benchmark máximo |
| OpenCV headless | 4.11.0.86 Apache-2.0 | Escala/contraste de píxeles CPU | Reutilizada; sin SSIM ni imagehash adicionales |
| Tesseract / pytesseract | 5.5.0 / 0.3.13, Apache-2.0 | OCR local; nuevo flujo usa stdin/stdout del binario | Gate global, 10 s/pasada; precisión real pendiente |
| Pillow | 12.3.0 MIT-CMU | Validación y ROI | Reutilizada; límites de píxeles |
| OR-Tools | 9.12.4544 Apache-2.0 | Motores matemáticos existentes | No cambia solver en etapa 1 |
| httpx | 0.28.1 BSD-3-Clause | Clientes locales existentes | No conector privado nuevo |
| React/TypeScript/Vite | Versiones fijadas en package-lock.json; MIT/Apache-2.0/MIT | UI y compilación en imagen | Reutilizados; 20 formularios renderizados |
| Zod/TanStack/Vitest/Playwright | Lockfile del proyecto; MIT | Contratos y pruebas propias | Sin automatización EA |
| getDisplayMedia | API del navegador | Solo host compatible/contexto seguro | Alternativa imagen manual; pantalla completa rechazada |
| Ollama | Compose heredado aún usa latest | Lenguaje opcional | No interviene en OCR ni commit; suite sin servicio. Fijar versión tras probar inferencia queda pendiente. |

Muestra de recursos (no benchmark): backend de API ~197,6 MiB/512 MiB en reposo durante verificación. No se midió el pico OCR real del propietario. PaddleOCR, ONNX, RapidFuzz, mss, BeautifulSoup/selectolax, Redis/Celery y OpenTelemetry **no instalados ni evaluados con A/B**; no hay evidencia que justifique su coste en este incremento. No se atribuyen licencias/versiones ni mejoras de exactitud a paquetes no probados.
