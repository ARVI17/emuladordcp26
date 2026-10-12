import json
import re
import httpx
from app.core.config import settings

UNAVAILABLE = "El asistente conversacional local no está disponible. Las funciones de inventario, DCP, objetivos y optimización continúan funcionando normalmente."
POLICY = 'fc27_grounded_v1'
FOCUSES = {'inventory': 'Resumen de mi club FC27', 'dcp': 'Revisar DCP FC27', 'protection': 'Revisar protecciones FC27'}


def question_focus(message):
    editions = re.findall(r'\b(?:ea\s*)?(?:fc|fifa|fut)[\s_-]*(\d{2,4})\b', message, re.I)
    if any(edition not in {'27', '2027'} for edition in editions):
        raise ValueError('Solo se admiten consultas FC27')
    lower = message.casefold()
    return 'protection' if any(word in lower for word in ('prote', 'titular')) else 'dcp' if any(word in lower for word in ('dcp', 'sbc', 'desafío')) else 'inventory'


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

async def status() -> dict:
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.get(f"{settings.ollama_url}/api/tags")
            return {"available": response.is_success, "model": settings.ollama_model}
    except Exception:
        return {"available": False, "model": settings.ollama_model}

async def chat(message: str, context: str) -> dict:
    if not (await status())["available"]: return {"available": False}
    prompt = 'Elige un enfoque FC27: inventory, dcp o protection. Devuelve solo JSON con focus.\n' + context + '\nIntención: ' + message
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                f"{settings.ollama_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": settings.ollama_keep_alive,
                    "format": {"type": "object", "properties": {"focus": {"type": "string", "enum": list(FOCUSES)}}, "required": ["focus"], "additionalProperties": False},
                },
            )
            response.raise_for_status()
            parsed = json.loads(response.json().get('response', '{}'))
            return {'available': True, 'focus': parsed.get('focus') if isinstance(parsed, dict) else None}
    except Exception:
        return {"available": False}
