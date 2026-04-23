import os
import logging
import asyncio
import hashlib
from datetime import datetime
from dotenv import load_dotenv
import httpx
from pathlib import Path
from collections import deque
from functools import lru_cache

# Загружаем .env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Получаем ключи
FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
API_KEY = os.getenv("YANDEX_API_KEY")

print("=" * 50)
print("YANDEX ANALYZER ИНИЦИАЛИЗАЦИЯ")
print(f"  FOLDER_ID: {FOLDER_ID}")
print(f"  API_KEY: {API_KEY[:20] if API_KEY else 'None'}...")
print("=" * 50)

if not API_KEY or not FOLDER_ID:
    logging.error("❌ Ключи YandexGPT не загружены!")

# ============= КЭШ И СТАТИСТИКА =============
_response_cache = {}
_cache_queue = deque(maxlen=100)
_usage_stats = {
    "total_requests": 0,
    "cached_responses": 0,
    "total_tokens": 0,
    "errors": 0
}

def get_cache_key(prompt: str, temperature: float, max_tokens: int) -> str:
    content = f"{prompt}|{temperature}|{max_tokens}"
    return hashlib.md5(content.encode()).hexdigest()

def get_usage_stats() -> dict:
    return {
        "total_requests": _usage_stats["total_requests"],
        "cached_responses": _usage_stats["cached_responses"],
        "cache_hit_rate": f"{(_usage_stats['cached_responses'] / _usage_stats['total_requests'] * 100):.1f}%" if _usage_stats["total_requests"] > 0 else "0%",
        "total_tokens": _usage_stats["total_tokens"],
        "errors": _usage_stats["errors"]
    }

# ============= ОСНОВНАЯ ФУНКЦИЯ =============
async def call_yandex_gpt(
    prompt: str, 
    image_bytes: bytes = None,
    temperature: float = 0.6,
    max_tokens: int = 2000,
    use_cache: bool = True,
    retry_count: int = 3,
    system_prompt: str = None
) -> str:
    
    if not API_KEY or not FOLDER_ID:
        return "❌ Ошибка: не настроены ключи YandexGPT."
    
    _usage_stats["total_requests"] += 1
    
    cache_key = get_cache_key(prompt, temperature, max_tokens)
    if use_cache and cache_key in _response_cache:
        _usage_stats["cached_responses"] += 1
        return _response_cache[cache_key]
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "text": system_prompt})
    messages.append({"role": "user", "text": prompt})
    
    headers = {
        "Authorization": f"Api-Key {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": max_tokens
        },
        "messages": messages
    }
    
    start_time = datetime.now()
    
    for attempt in range(retry_count):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                    headers=headers,
                    json=data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result["result"]["alternatives"][0]["message"]["text"]
                    
                    usage = result.get("result", {}).get("usage", {})
                    tokens = usage.get("totalTokens", 0)
                    _usage_stats["total_tokens"] += tokens
                    
                    if use_cache:
                        _response_cache[cache_key] = answer
                        _cache_queue.append(cache_key)
                    
                    return answer
                    
                elif response.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    error_text = await response.text()
                    if attempt < retry_count - 1:
                        await asyncio.sleep(1)
                        continue
                    return f"❌ Ошибка YandexGPT: {error_text[:200]}"
                    
        except Exception as e:
            _usage_stats["errors"] += 1
            if attempt < retry_count - 1:
                await asyncio.sleep(1)
                continue
            return f"❌ Ошибка: {str(e)}"
    
    return "❌ Не удалось получить ответ"

# ============= АНАЛИЗ ОБРАЗА =============
async def analyze_outfit(photo_bytes: bytes) -> str:
    system_prompt = """Ты — элитный стилист-эксперт в эстетике Old Money. Будь строгим, но конструктивным. Указывай конкретные детали."""
    
    prompt = """
Проанализируй образ на фото.

🧥 **ОБЩЕЕ ВПЕЧАТЛЕНИЕ** (2-3 предложения)

✅ **СИЛЬНЫЕ СТОРОНЫ** (3-5 пунктов)

❌ **ЧТО МОЖНО УЛУЧШИТЬ** (3-5 пунктов)

💡 **КОНКРЕТНЫЕ СОВЕТЫ** (3-5 пунктов)

📊 **ОЦЕНКА:** X/10
"""
    return await call_yandex_gpt(prompt, photo_bytes, temperature=0.6, max_tokens=2500, system_prompt=system_prompt)

async def analyze_item_for_purchase(photo_bytes: bytes) -> str:
    system_prompt = """Ты — эксперт по инвестиционному гардеробу."""
    
    prompt = """
Проанализируй вещь на фото.

🔍 **РАЗБОР**

✅ **БЕРИ, если:**
• условие 1

❌ **НЕ БЕРИ, если:**
• условие 1

🎯 **ВЕРДИКТ:** [ИНВЕСТИЦИЯ / НЕ БЕРИ]

⭐ **ОЦЕНКА:** X/10
"""
    return await call_yandex_gpt(prompt, photo_bytes, temperature=0.4, max_tokens=2000, system_prompt=system_prompt)

async def analyze_label(photo_bytes: bytes) -> str:
    system_prompt = """Ты — эксперт по текстилю."""
    
    prompt = """
Проанализируй этикетку.

🏷️ **СОСТАВ**
✅ **ПЛЮСЫ**
❌ **МИНУСЫ**
💰 **ВЕРДИКТ:** [ИНВЕСТИЦИЯ / НЕ БЕРИ]
"""
    return await call_yandex_gpt(prompt, photo_bytes, temperature=0.3, max_tokens=1500, system_prompt=system_prompt)