"""Own practice hypotheses; cited mechanics do not establish a universal meta."""
from datetime import date

SOURCES = {
    'R09': {'title': 'EA · Gameplay Deep Dive', 'url': 'https://www.ea.com/games/ea-sports-fc/fc-27/news/pitch-notes-fc27-gameplay-deep-dive', 'published_on': '2026-07-29', 'kind': 'official'},
    'R16': {'title': 'NealGuides · Defensa', 'url': 'https://nealguides.com/fc-27-defending-tips/', 'published_on': '2026-09-25', 'kind': 'creator_hypothesis'},
}
DRILLS = {
    'defending': {'title': 'Defensa manual', 'principle': 'En juego competitivo, EA da más responsabilidad al defensor controlado.', 'exercise': 'Repite diez situaciones de uno contra uno. Prueba mantener el ángulo de tiro cerrado antes de intentar recuperar.', 'error': 'Salir precipitadamente con el central.', 'metric': 'Ataques contenidos sin ocasión clara / intentos', 'references': ['R09', 'R16']},
    'switching': {'title': 'Cambio de jugador', 'principle': 'NealGuides propone anticipar el cambio antes del pase rival; es una hipótesis de práctica.', 'exercise': 'Repite diez ataques similares. Cambia al defensor elegido antes del pase y anota si llegas a cubrir la línea.', 'error': 'Cambiar cuando el balón ya superó al mediocampo.', 'metric': 'Líneas cubiertas a tiempo / intentos', 'references': ['R16']},
    'runs': {'title': 'Desmarques', 'principle': 'EA documenta desmarques curvos activados manualmente y de distancia limitada.', 'exercise': 'Ensaya diez desmarques desde la misma zona. Anota recepciones sin fuera de juego; varía solo el momento de activación.', 'error': 'Activar demasiado pronto y perder el espacio.', 'metric': 'Recepciones legales / intentos', 'references': ['R09'], 'controls': {'PlayStation': 'Pulsar L1 + R1', 'Xbox': 'Pulsar LB + RB'}},
    'passing': {'title': 'Pases y continuación', 'principle': 'EA describe pase seguido de carrera curva.', 'exercise': 'Ensaya diez paredes desde la misma posición. Cambia solo el instante del pase de vuelta y cuenta posesiones conservadas.', 'error': 'Devolver antes de que exista una línea de pase.', 'metric': 'Combinaciones completadas / intentos', 'references': ['R09'], 'controls': {'PlayStation': 'L1 + R1 + X', 'Xbox': 'LB + RB + A'}},
    'crossing': {'title': 'Centros', 'principle': 'EA describe centros dirigidos al espacio y mayor exigencia de precisión en remates de cabeza.', 'exercise': 'Repite diez centros desde la misma zona y con el mismo receptor. Varía solo la potencia y cuenta contactos limpios.', 'error': 'Cambiar potencia, posición y receptor a la vez.', 'metric': 'Contactos limpios / intentos', 'references': ['R09']},
    'playstyles': {'title': 'PlayStyles observados', 'principle': 'Ejercicio local de observación; no presupone que una carta tenga un estilo ni que garantice una animación.', 'exercise': 'Revisa el PlayStyle en tu carta y su descripción en el juego. Repite diez acciones de esa descripción y registra lo observado.', 'error': 'Atribuir un resultado al estilo sin comprobar carta y contexto.', 'metric': 'Acciones observadas según la descripción / intentos', 'references': []},
}


def catalog():
    return {'game_version': 'FC27', 'reviewed_on': '2026-10-11', 'patch_verified': False,
            'review_due': date.today() > date(2026, 10, 25), 'sources': SOURCES, 'drills': DRILLS,
            'notice': 'Ejercicios propios e hipótesis contrastables. Revisión documental del 11-oct-2026; no acredita tu parche ni configuración. Comprueba los controles en el juego.'}


def build_agenda(focus, minutes, platform):
    drill = DRILLS[focus]
    warmup = max(1, minutes // 5)
    review = max(1, minutes // 5)
    return {**catalog(), 'focus': focus, 'title': drill['title'], 'platform': platform,
            'minutes': minutes, 'exercise': drill['exercise'], 'metric': drill['metric'],
            'error': drill['error'], 'reference_ids': drill['references'],
            'control': drill.get('controls', {}).get(platform),
            'control_status': 'documented_reference_check_settings' if platform in drill.get('controls', {}) else 'pending_in_game_review',
            'steps': [{'minutes': warmup, 'task': 'Comprobar versión, controles y situación inicial.'},
                      {'minutes': minutes-warmup-review, 'task': drill['exercise']},
                      {'minutes': review, 'task': 'Anotar intentos, aciertos y un único ajuste para la siguiente sesión.'}]}
