import aiohttp

from .config import get_settings


settings = get_settings()

# обращение асинхронное к openrouter для ии
async def fetch_completion(history, model):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_key}",
        "HTTP-Referer": settings.app_name,
        "X-Title": settings.app_name,
    }
    payload = {"model": model, "messages": history, "stream": False}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers, timeout=120) as resp:
            data = await resp.json()
            choice = data.get("choices", [{}])[0]
            msg = choice.get("message", {})
            return msg.get("content") or "Нет ответа от модели"
