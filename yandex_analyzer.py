
import os
from dotenv import load_dotenv
from yandex_cloud_ml_sdk import YCloudML
import io
from PIL import Image

load_dotenv()

FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
API_KEY = os.getenv("YANDEX_API_KEY")

# Инициализация SDK
sdk = YandexAIStudio(folder_id=FOLDER_ID, auth=API_KEY)

# Получаем модель — используем lite версию (быстрее и дешевле)
model = sdk.models.completions("yandexgpt-lite")
model = model.configure(temperature=0.4, max_tokens=800)

async def analyze_outfit(photo_bytes):
    """Анализирует образ на фото"""
    
    prompt = """
Ты — профессиональный стилист в эстетике Old Money (тихая роскошь, вечная элегантность).

Проанализируй образ на фото и ответь строго в таком формате:

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
    
    try:
        # Для мультимодальности (фото + текст) потребуется другой подход
        # Пока отправляем только текст, а фото описываем в промпте
        result = sdk.completions.create(
        model="yandexgpy-lite",
        messages=[{"role": "user", "text": prompt}],
        temperature=0.4,
        max_tokens=800
        )
        return result.choices[0].message.text
    except Exception as e:
        return f"❌ Ошибка при анализе: {str(e)}"

async def analyze_item_for_purchase(photo_bytes):
    """Анализирует вещь для покупки: бери/не бери"""
    
    prompt = """
Ты — эксперт по качественным вещам и инвестиционному гардеробу.

Проанализируй вещь на фото и реши: стоит ли её покупать человеку, который хочет выглядеть в эстетике Old Money.

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
    
    try:
        result = sdk.completions.create(
        model="yandexgpy-lite",
        messages=[{"role": "user", "text": prompt}],
        temperature=0.4,
        max_tokens=800
        )
        return result.choices[0].message.text
    except Exception as e:
        return f"❌ Ошибка при анализе: {str(e)}"

async def analyze_label(photo_bytes):
    """Анализирует этикетку"""
    
    prompt = """
Ты — эксперт по тканям и качеству одежды.

На фото — этикетка одежды. Распознай, что написано на этикетке, и проанализируй состав.

Ответь строго в таком формате:

🏷️ **Анализ этикетки**

📋 **Состав:**
• [материал 1] — [процент]%
• [материал 2] — [процент]%

✅ **Плюсы:**
• [плюс 1]
• [плюс 2]

❌ **Минусы:**
• [минус 1]

💰 **Вердикт:** [ИНВЕСТИЦИЯ / СРЕДНЕЕ / НЕ БЕРИ]

Если распознать состав не удалось, напиши об этом и дай общие советы по выбору качественных тканей.
"""
    
    try:
        result = sdk.completions.create(
        model="yandexgpy-lite",
        messages=[{"role": "user", "text": prompt}],
        temperature=0.4,
        max_tokens=800
        )
        return result.choices[0].message.text
    except Exception as e:
        return f"❌ Ошибка при анализе этикетки: {str(e)}"