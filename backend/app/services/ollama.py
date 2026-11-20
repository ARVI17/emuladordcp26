import json
import re
import httpx
from app.core.config import settings

UNAVAILABLE = "El asistente conversacional local no está disponible. Las funciones de inventario, DCP, objetivos y optimización continúan funcionando normalmente."
POLICY = 'fc27_grounded_v1'
FOCUSES = {'inventory': 'Resumen de mi club FC27', 'dcp': 'Revisar DCP FC27', 'protection': 'Revisar protecciones FC27'}
SQUAD_INTENT = 'Explicar mi equipo propuesto'
PLANNING_INTENTS = {'dcp':'Revisar DCP FC27', 'market':'Revisar anuncios de consola', 'gallery':'Revisar mi Galería'}


def question_focus(message):
    editions = re.findall(r'\b(?:ea\s*)?(?:fc|fifa|fut)[\s_-]*(\d{2,4})\b', message, re.I)
    if any(edition not in {'27', '2027'} for edition in editions):
        raise ValueError('Solo se admiten consultas FC27')
    lower = message.casefold()
    if re.search(r'\b(?:prote\w*|candados?)\b', lower):
        return 'protection'
    if re.search(r'\b(?:dcps?|sbcs?|desaf[ií]os?)\b', lower):
        return 'dcp'
    if re.search(r'\b(?:galer[ií]a|gallery)\b', lower):
        return 'gallery'
    if re.search(r'\b(?:mercado|vender|ventas?|precio de|cotizaci[oó]n)\b', lower):
        return 'market'
    if re.search(r'\b(?:plantillas?|alineaci[oó]n|formaci[oó]n|equipos?|banquillo|suplentes?|once)\b', lower):
        return 'squad'
    return 'protection' if re.search(r'\btitular(?:es)?\b', lower) else 'inventory'


def grounded_answer(result, counts, focus):
    # Provider prose never becomes a factual FC27 answer, even after a provider change.
    proposed = result.get('focus')
    focus = proposed if isinstance(proposed, str) and proposed in FOCUSES else focus
    answer = f"DATOS FC27: {counts['players']} cartas activas verificadas; {counts['duplicates']} duplicados; {counts['protected']} protegidas; {counts['dcp']} DCP documentados pendientes."
    advice = {'inventory': 'Revisa las copias en Inventario antes de planificar.', 'dcp': 'Abre DCP para calcular una simulación con los requisitos vigentes.', 'protection': 'Revisa favoritos, titulares y plantillas protegidas antes de una simulación.'}[focus]
    answer += '\nRECOMENDACIÓN: ' + advice + '\nFALTANTES: integración del club real pendiente. No se infieren cartas, precios ni requisitos ausentes.'
    available = result.get('available') is True
    if not available:
        answer = UNAVAILABLE + '\n' + answer
    return {'available': available, 'answer': answer, 'sections': {'source': 'Resumen local FC27 validado', 'policy': POLICY}, 'game_version': 'FC27'}

def explain_squad(result, plan):
    squad = plan['squad']
    if not squad or not squad['lineup']:
        answer = 'Aún faltan cartas admitidas con puestos cubiertos en una formación vigente.'
    else:
        lineup = squad['lineup']
        best = max(lineup, key=lambda p: p['fit'])
        lines = dict(
            coverage=f"Quedan por cubrir {', '.join(p['position'] for p in squad['gaps'])}." if squad['gaps'] else 'Hay una carta elegible en cada puesto.',
            fit=f"{best['name']} tiene el mayor encaje calculado en este once como {best['position']} ({best['fit']:.1f}/100). {best['reason'].replace('; ', ' · ')}.",
            bench=f"El banquillo cubre {len(squad['bench'])} de 7 plazas con futbolistas distintos.")
        preferred = result.get('focus')
        first = preferred if isinstance(preferred, str) and preferred in lines else ('coverage' if squad['gaps'] else 'fit')
        answer = f"Con {plan['reviewed']} cartas revisadas, la {squad['formation']} cubre {len(lineup)} de 11 puestos sin compras. " + ' '.join([lines[first], *(v for k, v in lines.items() if k != first)])
    return dict(available=result.get('available') is True, answer=answer,
                sections=dict(source='Simulación local por puesto', policy=POLICY), game_version='FC27')


async def status() -> dict:
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.get(f"{settings.ollama_url}/api/tags")
            return {"available": response.is_success, "model": settings.ollama_model}
    except Exception:
        return {"available": False, "model": settings.ollama_model}

async def chat(message: str, context: str) -> dict:
    if not (await status())["available"]: return {"available": False}
    choices = ['coverage', 'fit', 'bench'] if message == 'squad' else list(FOCUSES)
    prompt = 'Elige el aspecto más útil para explicar al técnico entre ' + ', '.join(choices) + '. Devuelve solo JSON con focus.\n' + context + '\nIntención: ' + message
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                f"{settings.ollama_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": settings.ollama_keep_alive,
                    "format": {"type": "object", "properties": {"focus": {"type": "string", "enum": choices}}, "required": ["focus"], "additionalProperties": False},
                },
            )
            response.raise_for_status()
            parsed = json.loads(response.json().get('response', '{}'))
            return {'available': True, 'focus': parsed.get('focus') if isinstance(parsed, dict) else None}
    except Exception:
        return {"available": False}
