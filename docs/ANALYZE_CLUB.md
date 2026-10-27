# Analizar mi club · extensión 0.5.0 / esquema 0020

## Estado real

La instalación personal se comprobó el 27-oct-2026 en **http://localhost:8090**, frontend/API **ea27c61**, esquema **0019**, cinco servicios saludables. Este sprint prepara una actualización; no la despliega sin autorización específica. No hay sesión de navegador personal conectada a Codex. **Cero cartas personales contrastadas en este sprint.** Las pruebas de motor y navegador usan muestras sintéticas.

## Acción única y etapas

Inicio y el panel ofrecen **Analizar mi club**. La SPA crea o reanuda un checkpoint PostgreSQL por contexto y ejecuta los cálculos locales. El panel emparejado consulta ese checkpoint local; si tiene permiso de pestaña inicia el lector aplicable. Sin permiso muestra el gesto necesario. Con una vista EA, genera únicamente el diagnóstico estructural y comunica que faltan un mecanismo de lectura automática permitido y un perfil contrastado. No declara conectado, sincronizado ni leído el club.

Las etapas distinguen contexto/permiso, reconocimiento, lectura, admisión, principal y cálculo. La cobertura separa siete dominios, observaciones, ámbitos página/filtro/ubicación y revisión. Sus contadores no son cartas únicas ni el total indicado por la pantalla. Las últimas 1.000 observaciones forman la ventana del resumen, expresamente parcial. Un campo conocido conserva su procedencia; `source_updated_at` sigue siendo nulo.

## Lectura permitida de prueba y exportación propia

El perfil automático implementado reconoce **solo el esquema propio documentado de `/reader-sample.html`**, con una región `data-club-lab-sample="1"`, edición, origen, vista y campos `data-field`. Cubre cabecera/cuenta, inventario, ficha, plantilla, DCP, objetivo y Galería mediante las mismas definiciones y `extractProfile` que usan las pruebas. No son selectores EA. Los mapas manuales y sus pruebas anteriores siguen disponibles en **Diagnóstico técnico y perfiles avanzados**.

Se comprueba estabilidad dos veces, con 250 ms entre muestras, tras debounce de 700 ms. El observer solo observa la región autorizada y emite un aviso sin datos; el worker extrae y fragmenta. No lee almacenamiento de la página, red autenticada, formularios, iframes ni scripts. No pulsa controles ni desplaza la página. Las páginas mostradas por el usuario actualizan el mismo recorrido; un cambio de contexto declarado, estructura inválida o pérdida del documento detiene la lectura. La detección de cuenta real sigue sin probarse.

Hasta 300 registros, 30 por fragmento, diez fragmentos; 128 KB por fragmento y cola de 100 fragmentos/2 MB. El inspector recorre como máximo 8.000 nodos, incluye 4.000, profundidad siete y 950 KB; no recorta una región para admitirla como completa. Los mapas manuales guardados conservan además su límite de 512 KB. Cien firmas recientes evitan relecturas idénticas; la deduplicación del servidor sigue aplicándose fuera de esa ventana. La cola se escribe antes del envío y conserva IDs, hash y fecha tras una caída del worker. El panel reintenta con backoff local. No hay observer persistente si el usuario lo pausa, cancela o revoca.

## Revisión inicial e incrementos

La primera región siempre se revisa por lote en Mi cuenta. Una casilla opcional autoriza incorporar listas de inventario posteriores **sin conflictos** del mismo contexto, concesión, dominio, origen, idioma, estructura y revisión exacta del perfil. No transfiere confianza de muestras a datos observados ni entre cuentas. La autorización queda en `reader_workflows.trusted_profiles` y no convierte un perfil en verificación del proveedor.

Solo inventario ubicado en el club admite este proceso. Cuenta/saldo, plantilla, requisitos, Galería y salón de ventas conservan revisión. Las identidades repetidas, campos contradictorios, copias retiradas o no disponibles quedan pendientes; no se crean copias ambiguas automáticamente ni se resucitan consumidas. Falta de una carta en una página no produce bajas. Una nueva generación de sesión conserva el checkpoint como pausado e invalida sus autorizaciones. Cancelar borra estas autorizaciones, conserva historial/cola y detiene la admisión automática; reanudar requiere aprobar otra vez si se canceló.

## Cálculos y principal

El análisis reutiliza `squad_profiles`, `simulate_dcp`, `objective_preview` y la evaluación de escenarios de Galería. Calcula equipos alternativos y banquillos, hasta tres DCP revisados y tres objetivos revisados recientes por ejecución. La ausencia o caducidad de reglas/datos produce un impedimento concreto. Las restricciones conservan los validadores existentes; el modelo CP-SAT no recibe instrucciones de la web. No se aplican consumos ni progreso. Las alternativas pueden reutilizar titulares para jugar. La comparación de hash/revisión determina si la principal **local** sigue sin cambios; no acredita el estado externo de EA.

Evoluciones y mercado conservan sus módulos existentes y sus revisiones específicas; este primer orquestador señala sus datos pendientes, no elige automáticamente una Evo ni una compra. La comparación económica automática transversal, rutas de Evos y estrategias específicas adicionales quedan pendientes de integrar al botón. No se realiza una llamada LLM/OCR por carta.

La referencia pública [Birmingham City](https://www.fut.gg/fut-gallery/premier-league/birmingham-city/), consultada el 27-oct-2026, indica 15 futbolistas del equipo femenino, umbrales D/C/B/A/S 10/300/500/700/1.000 y premios B/A/S 5/8/15 fichas. El resumen conserva esos hechos de referencia separados del historial personal y deja posesión, progreso y costes desconocidos. No se importan las cartas públicas ni se convierten `000,000` en cero. Bonificaciones completas, redondeo e inventario propio siguen siendo necesarios para una ruta económica acreditada.

## Diagnóstico mínimo y evidencia real pendiente

**Generar diagnóstico mínimo** crea y descarga, en una acción, un JSON estructural privado. Solo contiene etiquetas HTML comunes, roles, clases de vocabulario deportivo cerrado, relaciones padre/hijo y contadores acotados. No contiene texto, nombres de jugadores, IDs, etiquetas accesibles, href/src, HTML bruto, capturas ni credenciales. Las entradas visibles de acceso, MFA o pago bloquean el diagnóstico; los demás formularios se omiten como subárboles. Un selector probable no es un extractor validado; activar un borrador o pasar un fixture tampoco lo convierte en tal.

Las [normas EA](https://help.ea.com/es/articles/ea-sports-fc/fc-rules/) y la [Community API](https://help.ea.com/en/articles/ea-sports-fc/community-api/) se consultaron el 27-oct-2026. No hay mecanismo acreditado de autorización EA para el lector automático de este proyecto. `activeTab` es un permiso temporal del navegador, no aprobación del servicio. No se heredan permisos de sus socios. La extensión no navega automáticamente en EA ni compra, vende, entrega, reclama, abre sobres, aplica Evos o cambia la principal.

## Contratos y operación

- `POST /club/analyze`, `GET /club/analysis-workflow`, `POST /club/analysis-workflow/action`: sesión local/CSRF y contexto.
- `/reader/workflow`, `/start`, `/action`, `/view`, `/refresh`: concesión vigente del lector. `/view` solo acepta estados enumerados y límites; no recibe texto de la página ni acredita identidad.
- `POST /reader/observations/{id}/review` añade `enable_incremental=false` por defecto. V1 y V2 siguen compatibles.
- Migración aditiva **0020**: una tabla `reader_workflows`; ningún dato existente cambia de esquema o edición.
- Empaquetado: `python scripts/package_reader.py state/sprints/<pase>/result.json`, desde la imagen compilada que pasó Playwright. Instalar la carpeta `chrome-mv3` mediante Cargar descomprimida. El diagnóstico no necesita backend nuevo; el botón completo requiere 0020.

Los resultados realmente ejecutados se registran en [TESTING.md](TESTING.md). H2–H4 sobre el club personal permanecen pendientes: faltan autorización aplicable, muestra real y contraste de cartas/reglas/cobertura. La infraestructura sintética no se presenta como aprobación de esos hitos.
