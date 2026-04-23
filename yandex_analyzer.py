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
    """Отправляет запрос к YandexGPT и возвращает ответ."""
    
    if not API_KEY or not FOLDER_ID:
        logging.error("YANDEX_API_KEY или YANDEX_FOLDER_ID не найдены")
        return "❌ Ошибка: не настроены ключи YandexGPT. Пожалуйста, сообщите администратору."
    
    headers = {
        "Authorization": f"Api-Key {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Формируем тело запроса
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
    
    # Логируем для отладки (без敏感ных данных)
    logging.info(f"Отправка запроса к YandexGPT. Folder ID: {FOLDER_ID[:10]}...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(YANDEX_GPT_URL, headers=headers, json=data)
            
            # Логируем статус ответа
            logging.info(f"YandexGPT ответ: статус {response.status_code}")
            
            # Пытаемся получить тело ответа
            try:
                result = response.json()
                logging.info(f"Тело ответа: {str(result)[:500]}")  # Логируем первые 500 символов
            except:
                logging.error(f"Не удалось распарсить JSON: {response.text[:500]}")
                result = None
            
            if response.status_code == 200:
                if result and "result" in result and "alternatives" in result["result"]:
                    return result["result"]["alternatives"][0]["message"]["text"]
                else:
                    logging.error(f"Неожиданный формат ответа: {result}")
                    return "❌ Ошибка: неожиданный формат ответа от YandexGPT"
            else:
                # Разбираем конкретную ошибку
                error_msg = "Неизвестная ошибка"
                if result:
                    if "message" in result:
                        error_msg = result["message"]
                    elif "error" in result:
                        error_msg = result["error"].get("message", str(result["error"]))
                    elif "description" in result:
                        error_msg = result["description"]
                
                logging.error(f"YandexGPT ошибка {response.status_code}: {error_msg}")
                
                # Даём понятное объяснение пользователю
                if response.status_code == 400:
                    if "folder" in error_msg.lower():
                        return "❌ Ошибка: неверный идентификатор каталога (Folder ID). Проверьте настройки бота."
                    elif "api" in error_msg.lower() or "key" in error_msg.lower():
                        return "❌ Ошибка: неверный API-ключ. Проверьте настройки бота."
                    else:
                        return f"❌ Ошибка запроса: {error_msg}"
                elif response.status_code == 401:
                    return "❌ Ошибка авторизации: недействительный API-ключ."
                elif response.status_code == 403:
                    return "❌ Ошибка доступа: у сервисного аккаунта нет прав на использование YandexGPT. Нужна роль 'ai.languageModels.user'."
                elif response.status_code == 429:
                    return "❌ Превышен лимит запросов. Попробуйте позже."
                else:
                    return f"❌ Ошибка YandexGPT (код {response.status_code}): {error_msg}"
                
    except httpx.TimeoutException:
        logging.error("Таймаут при вызове YandexGPT")
        return "❌ Превышено время ожидания ответа от YandexGPT. Попробуйте ещё раз."
    except Exception as e:
        logging.error(f"Исключение при вызове YandexGPT: {e}", exc_info=True)
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
    