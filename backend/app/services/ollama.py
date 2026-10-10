import httpx
from app.core.config import settings

UNAVAILABLE = "El asistente conversacional local no está disponible. Las funciones de inventario, DCP, objetivos y optimización continúan funcionando normalmente."

async def status() -> dict:
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.get(f"{settings.ollama_url}/api/tags")
            return {"available": response.is_success, "model": settings.ollama_model}
    except Exception:
        return {"available": False, "model": settings.ollama_model}

async def chat(message: str, context: str) -> dict:
    if not (await status())["available"]: return {"available": False, "answer": UNAVAILABLE, "sections": {}}
    prompt = "Eres un asistente local de FC. Distingue DATOS, RECOMENDACIÓN, SUPOSICIONES y FALTANTES. No afirmes datos no presentes.\n" + context + "\nPregunta: " + message
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                f"{settings.ollama_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": settings.ollama_keep_alive,
                },
            )
            response.raise_for_status()
            return {"available": True, "answer": response.json().get("response", ""), "sections": {"source": "Ollama local"}}
    except Exception:
        return {"available": False, "answer": UNAVAILABLE, "sections": {}}
