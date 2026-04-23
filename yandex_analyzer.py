import os
import logging
from dotenv import load_dotenv
import httpx
import base64
from pathlib import Path

# Загружаем .env принудительно
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
API_KEY = os.getenv("YANDEX_API_KEY")

# Диагностика (удалите после проверки)
print(f"[yandex_analyzer] FOLDER_ID: {FOLDER_ID}")
print(f"[yandex_analyzer] API_KEY: {API_KEY[:20] if API_KEY else 'None'}...")

if not API_KEY or not FOLDER_ID:
    logging.error("❌ Ключи YandexGPT не загружены!")
    raise ValueError("YANDEX_API_KEY и YANDEX_FOLDER_ID должны быть в .env")

async def call_yandex_gpt(prompt: str, image_bytes: bytes = None) -> str:
    """Отправляет запрос к YandexGPT и возвращает ответ."""
    
    headers = {
        "Authorization": f"Api-Key {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.4,
            "maxTokens": 1000
        },
        "messages": [
            {
                "role": "user",
                "text": prompt
            }
        ]
    }
    
    # Если есть фото, пытаемся добавить (но yandexgpt-lite не поддерживает изображения)
    if image_bytes:
        logging.warning("YandexGPT Lite не поддерживает изображения. Отправляю только текстовый запрос.")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["result"]["alternatives"][0]["message"]["text"]
            else:
                error_text = await response.text()
                logging.error(f"YandexGPT ошибка {response.status_code}: {error_text}")
                return f"❌ Ошибка YandexGPT: {error_text[:200]}"
                
    except httpx.TimeoutException:
        return "❌ Превышено время ожидания ответа от YandexGPT."
    except Exception as e:
        logging.error(f"Ошибка при вызове YandexGPT: {e}")
        return f"❌ Ошибка при анализе: {str(e)}"

async def analyze_outfit(photo_bytes: bytes) -> str:
    prompt = """
Ты — профессиональный стилист в эстетике Old Money.

Ответь строго в формате:

🧥 **Анализ образа**

✅ **Что хорошо:**
• пункт 1
• пункт 2

❌ **Что можно улучшить:**
• пункт 1
• пункт 2

💡 **Советы:**
• совет 1
• совет 2
"""
    return await call_yandex_gpt(prompt, photo_bytes)

async def analyze_item_for_purchase(photo_bytes: bytes) -> str:
    prompt = """
Ты — эксперт по инвестиционным покупкам.

Ответь строго в формате:

💰 **Вердикт:** [БЕРИ / НЕ БЕРИ]

**Почему:**
• причина 1
• причина 2
"""
    return await call_yandex_gpt(prompt, photo_bytes)

async def analyze_label(photo_bytes: bytes) -> str:
    prompt = """
Ты — эксперт по тканям.

Проанализируй состав и скажи, качественная ли вещь.
"""
    return await call_yandex_gpt(prompt, photo_bytes)
    