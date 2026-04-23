import os
import logging
from dotenv import load_dotenv
import httpx
import base64

load_dotenv()

FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
API_KEY = os.getenv("YANDEX_API_KEY")

# API endpoint для YandexGPT
YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

async def call_yandex_gpt(prompt: str, image_bytes: bytes = None) -> str:
    """Отправляет запрос к YandexGPT с возможностью прикрепить фото и возвращает ответ."""
    
    if not API_KEY or not FOLDER_ID:
        logging.error("YANDEX_API_KEY или YANDEX_FOLDER_ID не найдены")
        return "❌ Ошибка: не настроены ключи YandexGPT. Пожалуйста, сообщите администратору."
    
    headers = {
        "Authorization": f"Api-Key {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Формируем сообщение
    if image_bytes:
        # Кодируем фото в base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # YandexGPT мультимодальная версия
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
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image",
                            "image": image_base64
                        }
                    ]
                }
            ]
        }
    else:
        # Только текст
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
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(YANDEX_GPT_URL, headers=headers, json=data)
            result = response.json()
            
            if response.status_code == 200:
                return result["result"]["alternatives"][0]["message"]["text"]
            else:
                error_msg = result.get("message", "Неизвестная ошибка")
                logging.error(f"YandexGPT ошибка {response.status_code}: {error_msg}")
                return f"❌ Ошибка YandexGPT: {error_msg}"
                
    except httpx.TimeoutException:
        return "❌ Превышено время ожидания ответа от YandexGPT. Попробуйте ещё раз."
    except Exception as e:
        logging.error(f"Ошибка при вызове YandexGPT: {e}")
        return f"❌ Ошибка при анализе: {str(e)}"

async def analyze_outfit(photo_bytes: bytes) -> str:
    """Анализирует образ на фото и даёт стилистические рекомендации."""
    
    prompt = """
Ты — профессиональный стилист в эстетике Old Money (тихая роскошь, вечная элегантность).

Проанализируй образ человека на этом фото, основываясь на принципах Old Money.

Ответь строго в таком формате:

🧥 **Анализ образа**

✅ **Что хорошо:**
• [пункт 1]
• [пункт 2]

❌ **Что можно улучшить:**
• [пункт 1]
• [пункт 2]

💡 **Советы:**
• [конкретная рекомендация 1]
• [конкретная рекомендация 2]

💰 **Совет по экономии:**
[один совет, как сэкономить деньги в контексте этого образа]

Будь строгой, но доброжелательной. Основывайся на принципах Old Money: качественные материалы, классические силуэты, отсутствие кричащих логотипов, нейтральная цветовая гамма.
"""
    
    return await call_yandex_gpt(prompt, photo_bytes)

async def analyze_item_for_purchase(photo_bytes: bytes) -> str:
    """Анализирует вещь для покупки: стоит брать или нет."""
    
    prompt = """
Ты — эксперт по качественным вещам и инвестиционному гардеробу.

Проанализируй вещь на этом фото и реши: стоит ли её покупать человеку, который хочет выглядеть в эстетике Old Money.

Ответь строго в таком формате:

🧥 **Анализ вещи**

✅ **БЕРИ, если:**
• [условие 1]
• [условие 2]

❌ **НЕ БЕРИ, если:**
• [условие 1]
• [условие 2]

💰 **Вердикт:** [ИНВЕСТИЦИЯ / СРЕДНЕЕ / НЕ БЕРИ]

[Краткое объяснение вердикта в 1 предложении]

Критерии оценки: качество материалов, классический крой, нейтральные цвета, долговечность, отсутствие логотипов.
"""
    
    return await call_yandex_gpt(prompt, photo_bytes)

async def analyze_label(photo_bytes: bytes) -> str:
    """Анализирует этикетку: оценивает состав и качество ткани."""
    
    prompt = """
Ты — эксперт по тканям и качеству одежды.

Проанализируй этикетку на этом фото (состав ткани, производитель, инструкции по уходу).

Ответь строго в таком формате:

🏷️ **Анализ этикетки**

📋 **Состав:**
• [материал 1]
• [материал 2]

✅ **Плюсы:**
• [плюс 1]
• [плюс 2]

❌ **Минусы:**
• [минус 1]

💰 **Вердикт:** [ИНВЕСТИЦИЯ / СРЕДНЕЕ / НЕ БЕРИ]

[Объяснение: вещь качественная/некачественная, будет ли служить долго]

Если точный состав не видно на фото, дай общие советы по выбору качественных тканей для эстетики Old Money.
"""
    
    return await call_yandex_gpt(prompt, photo_bytes)
    