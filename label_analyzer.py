import pytesseract
import platform
from PIL import Image
import io
import re

# Укажите путь к Tesseract (для Mac)
# pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'

async def analyze_label(photo_bytes):
    """Анализирует фото этикетки: распознаёт состав и даёт рекомендацию."""
    
    # 1. Открываем изображение
    image = Image.open(io.BytesIO(photo_bytes))
    
    # 2. Распознаём текст (русский + английский)
    extracted_text = pytesseract.image_to_string(image, lang='rus+eng')
    
    if not extracted_text.strip():
        return "❌ Не удалось распознать текст на этикетке.\nПопробуйте сфотографировать крупнее и при хорошем освещении."
    
    # 3. Анализируем состав
    analysis = parse_composition(extracted_text)
    
    return analysis

def parse_composition(text):
    """Парсит состав одежды из распознанного текста."""
    text = text.lower()
    
    # Ищем проценты и материалы
    composition_pattern = r'(\d+)%?\s*([а-яё]+)'
    matches = re.findall(composition_pattern, text)
    
    materials = []
    for percent, material in matches:
        materials.append({
            'material': material.strip(),
            'percent': int(percent)
        })
    
    # Если не нашли через regex, ищем ключевые слова
    if not materials:
        materials = find_materials_by_keywords(text)
    
    # 4. Оценка качества
    quality_score = calculate_quality_score(materials)
    
    # 5. Формируем ответ
    return format_response(materials, quality_score, text)

def find_materials_by_keywords(text):
    """Ищет материалы по ключевым словам."""
    material_keywords = {
        'шерсть': 'wool', 'хлопок': 'cotton', 'лён': 'linen',
        'шёлк': 'silk', 'кашемир': 'cashmere', 'вискоза': 'viscose',
        'полиэстер': 'polyester', 'нейлон': 'nylon', 'акрил': 'acrylic',
        'эластан': 'elastane', 'ангора': 'angora', 'мохер': 'mohair'
    }
    
    found = []
    for keyword_ru, keyword_en in material_keywords.items():
        if keyword_ru in text:
            found.append({'material': keyword_ru, 'percent': None})
    
    return found

def calculate_quality_score(materials):
    """Рассчитывает оценку качества от 0 до 10."""
    if not materials:
        return 5  # нейтральная оценка, если не распознали
    
    score = 0
    recommendations = []
    
    # Штрафы и бонусы за материалы
    for m in materials:
        material = m['material'].lower()
        
        # Премиальные материалы (бонус)
        if material in ['кашемир', 'шёлк', 'ангора', 'мохер', 'лён']:
            score += 3
            recommendations.append(f"✅ {material.capitalize()} — премиальный материал")
        
        # Хорошие натуральные материалы
        elif material in ['шерсть', 'хлопок', 'вискоза']:
            score += 2
            recommendations.append(f"✅ {material.capitalize()} — качественный натуральный материал")
        
        # Синтетика (штраф)
        elif material in ['полиэстер', 'нейлон', 'акрил']:
            score -= 1
            recommendations.append(f"⚠️ {material.capitalize()} — синтетика, хуже дышит")
    
    # Ограничиваем оценку
    score = max(0, min(10, score))
    
    return {'score': score, 'recommendations': recommendations}

def format_response(materials, quality, raw_text):
    """Форматирует ответ для пользователя."""
    
    # Блок с составом
    composition_block = "📋 **Состав:**\n"
    if materials:
        for m in materials:
            percent_str = f" {m['percent']}%" if m['percent'] else ""
            composition_block += f"• {m['material'].capitalize()}{percent_str}\n"
    else:
        composition_block += "• Не удалось точно определить состав\n"
        composition_block += f"*Распознанный текст:*\n`{raw_text[:200]}`\n"
    
    # Блок с плюсами/минусами
    pros_cons = "📊 **Анализ:**\n"
    if quality['recommendations']:
        for rec in quality['recommendations']:
            pros_cons += f"{rec}\n"
    else:
        pros_cons += "• Не удалось определить качество материалов\n"
    
    # Вердикт
    verdict_block = "💰 **Вердикт:**\n"
    if quality['score'] >= 7:
        verdict_block += "✅ **ИНВЕСТИЦИЯ**\nКачественный материал, вещь прослужит долго.\nБерите!"
    elif quality['score'] >= 4:
        verdict_block += "⚠️ **СРЕДНЕЕ КАЧЕСТВО**\nНормально для повседневной носки, но не ждите долговечности."
    else:
        verdict_block += "❌ **НЕ БЕРИТЕ**\nНизкокачественные материалы. Потратите деньги зря."
    
    return f"{composition_block}\n{pros_cons}\n{verdict_block}"