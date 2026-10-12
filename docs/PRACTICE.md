# Práctica FC27 y diario local

En Planes, «Rutina de práctica FC27» prepara una sesión de 5–90 minutos con una técnica, plataforma, ejercicio y métrica. Guarda su agenda y fuentes como snapshot; registrar el resultado no modifica cartas ni tácticas del juego. Solo una transición desde pendiente permite completar o cancelar. Una sesión completada puede vincularse al diario del mismo club y edición.

Las mecánicas citadas se contrastaron el 11-oct-2026 con [EA Gameplay Deep Dive, 29-jul-2026](https://www.ea.com/games/ea-sports-fc/fc-27/news/pitch-notes-fc27-gameplay-deep-dive) y el consejo de anticipar cambios con [NealGuides, 25-sep-2026](https://nealguides.com/fc-27-defending-tips/). Los ejercicios y reparto de tiempo son propuestas locales, no una pauta oficial ni una promesa de resultados. La ficha indica revisión pendiente después de 14 días y nunca acredita el parche instalado. Las combinaciones de botones citadas corresponden únicamente a PlayStation/Xbox; PC, Switch y las otras técnicas exigen comprobar la configuración del juego. El ejercicio de PlayStyles exige observar la carta y su descripción, sin inventar estilos poseídos.

Después del 25-oct-2026 se ocultan las instrucciones y sesiones con evidencia vencida y se rechazan nuevas agendas hasta una nueva revisión técnica. El histórico se conserva. La versión/parche real del dispositivo continúa sin acreditar.

El diario agrupa los últimos 100 partidos FC27 por táctica y cambio probado, muestra tamaño de muestra, minutos y tasas por 90 minutos. La comparación A/B es descriptiva: rival, dificultad y otras variables no están controladas. Los registros de otras ediciones o sin edición demostrable se preservan ocultos, sin contarlos ni etiquetarlos FC27 a partir del perfil actual.

Contratos: `GET /practice/catalog`, `GET/POST /practice/sessions`, `POST /practice/sessions/{id}/result`, `GET/POST /matches`. El filtro opcional `edition` de `/matches` solo acepta FC27; nunca cambia el contexto de club. La migración `0011` añade sesiones y vínculo/edición al diario sin eliminar registros. Restaurar requiere el dump y código previos, conforme a [FC27_UPGRADE.md](FC27_UPGRADE.md).
