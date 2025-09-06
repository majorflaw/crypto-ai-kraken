# src/agent/groq_client.py  (OpenAI-compatible Groq endpoint)
import httpx, asyncio
from src.utils.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"  # Groq supports OpenAI-style API

async def groq_hello():
    async with httpx.AsyncClient(timeout=30.0, headers={
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json"
    }) as client:
        payload = {
            "model": "openai/gpt-oss-20b",
            "messages": [{"role": "user", "content": "Reply with 'pong'"}],
            "temperature": 0
        }
        r = await client.post(GROQ_URL, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()