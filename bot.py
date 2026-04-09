import socket
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from yandex_analyzer import analyze_outfit, analyze_item_for_purchase, analyze_label
import database
import payment
import analyzer  # ваш модуль с AI-анализом


load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

database.init_db()

from label_analyzer import analyze_label  # импорт новой функции

async def handle_label(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для команды /label — анализ этикетки"""
    user_id = update.effective_user.id
    
    # Проверяем подписку
    has_subscription = database.has_active_subscription(user_id)
    has_free_left = database.has_free_consultation(user_id)
    
    if not has_subscription and not has_free_left:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📆 Оформить подписку 599₽/мес", callback_data="subscribe")]
        ])
        await update.message.reply_text(
            "🔍 Функция «Анализ этикетки» доступна только по подписке.\n\n"
            "Оформите подписку за 599₽ и получайте:\n"
            "✅ Анализ состава тканей\n"
            "✅ Оценку качества материалов\n"
            "✅ Вердикт: стоит ли покупать",
            reply_markup=keyboard
        )
        return
    
    # Получаем фото
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text(
            "📸 Как пользоваться:\n"
            "1. Отправьте фото этикетки в чат\n"
            "2. Нажмите на фото → 'Ответить'\n"
            "3. Напишите /label\n\n"
            "Или просто отправьте фото с подписью /label"
        )
        return
    
    # Берём фото из ответа
    photo_file = await update.message.reply_to_message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    await update.message.reply_text("🏷️ Анализирую этикетку... Это займёт несколько секунд.")
    
    # Анализируем
    analysis = await analyze_label(photo_bytes)
    await update.message.reply_text(analysis, parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    database.save_user(user.id, user.username, user.first_name, user.last_name)
    
    await update.message.reply_text(
        "🧥 Добро пожаловать в «Стиль вне времени» — вашего AI-стилиста в эстетике Old Money.\n\n"
        "🎁 Первая консультация — БЕСПЛАТНО.\n"
        "Вы отправляете фото - я даю полный разбор образа.\n\n"
        "После этого вы можете оформить подписку:\n"
        "📆 Подписка — 599₽/мес, неограниченные консультации.\n\n"
        "Что вы получите по подписке:\n"
        "✅ Анализ любых ваших образов\n"
        "✅ Советы по улучшению (ткани, цвета, силуэты)\n"
        "✅ Разбор ошибок, которые выдают отсутствие вкуса\n"
        "✅ Рекомендации по инвестиционным покупкам\n\n"
        "🚀 Отправьте первое фото прямо сейчас!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Справка\n\n"
        "🎁 Бесплатная консультация — 1 раз для каждого пользователя.\n"
        "📆 Подписка — 599₽/мес, неограниченные консультации.\n\n"
        "Как оформить подписку:\n"
        "1. Получите бесплатный разбор\n"
        "2. Бот предложит оплатить подписку\n"
        "3. Нажмите кнопку и оплатите через ЮKassa\n\n"
        "Как отключить подписку?\n"
        "Напишите @itsmedi19\n\n"
        "Команды:\n"
        "/start — главное меню\n"
        "/help — эта справка\n"
        "/status — статус вашей подписки"
        "/label — анализ этикетки: состав, качество ткани, вердикт"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    info = database.get_subscription_info(user_id)
    
    if info["active"]:
        end_date = datetime.fromisoformat(info["end_date"])
        days_left = (end_date - datetime.now()).days
        await update.message.reply_text(
            f"✅ Ваша подписка активна до {end_date.strftime('%d.%m.%Y')}\n"
            f"📆 Осталось дней: {days_left}\n\n"
            f"Отправляйте фото в любое время — я всегда готов помочь!"
        )
    else:
        # Проверяем, была ли бесплатная консультация
        has_free = not database.has_free_consultation(user_id)
        if not has_free:
            await update.message.reply_text(
                "❌ У вас нет активной подписки.\n\n"
                "🎁 Вы ещё не использовали бесплатную консультацию? Отправьте фото!"
            )
        else:
            await update.message.reply_text(
                "❌ У вас нет активной подписки.\n\n"
                "💳 Оформите подписку за 599₽/мес и получайте неограниченные консультации.\n"
                "Отправьте новое фото, чтобы увидеть предложение."
            )
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Основной обработчик фото"""
    user_id = update.effective_user.id
    
    # Проверяем, в каком режиме пользователь
    if context.user_data.get("waiting_for_check_photo"):
        # Пользователь хочет проверить вещь (бери/не бери)
        await handle_check_photo(update, context)
        return
    
    if context.user_data.get("waiting_for_label_photo"):
        # Пользователь хочет проверить этикетку
        await handle_label_photo(update, context)
        return
    
    # Если нет активного режима — проверяем подписку для обычного анализа
    has_subscription = database.has_active_subscription(user_id)
    has_free_left = database.has_free_consultation(user_id)
    
    if not has_subscription and not has_free_left:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📆 Оформить подписку 599₽/мес", callback_data="subscribe")]
        ])
        await update.message.reply_text(
            "❌ У вас нет активной подписки.\n\n"
            "Оформите подписку за 599₽ и получайте неограниченные консультации.",
            reply_markup=keyboard
        )
        return
    
    # Получаем фото
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    # Анализируем образ
    await update.message.reply_text("🔍 Анализирую ваш образ...")
    
    if has_free_left and not has_subscription:
        # Это бесплатная консультация
        analysis = await analyze_outfit(photo_bytes)
        database.save_consultation(user_id, update.message.photo[-1].file_id, analysis, is_free=True)
        await update.message.reply_text(analysis)
        
        # Предлагаем подписку
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📆 Оформить подписку 599₽/мес", callback_data="subscribe")]
        ])
        await update.message.reply_text(
            "✨ Понравился разбор?\n\n"
            "Оформите подписку за 599₽ и получайте неограниченные консультации.",
            reply_markup=keyboard
        )
    else:
        # Обычная платная консультация
        analysis = await analyze_outfit(photo_bytes)
        database.save_consultation(user_id, update.message.photo[-1].file_id, analysis, is_free=False)
        await update.message.reply_text(analysis)

async def handle_check_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает фото для команды /check"""
    user_id = update.effective_user.id
    
    # Проверяем, что пользователь действительно ждёт анализа
    if not context.user_data.get("waiting_for_check_photo"):
        # Не в режиме /check — игнорируем или перенаправляем
        await update.message.reply_text(
            "Отправьте /check, чтобы проанализировать вещь, или просто фото для разбора образа."
        )
        return
    
    # Получаем фото
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    await update.message.reply_text("🔍 Анализирую вещь... Это займёт несколько секунд.")
    
    # Временная заглушка (потом заменим на AI)
    analysis = get_item_analysis_stub()
    
    await update.message.reply_text(analysis)
    
    # Сбрасываем состояние
    context.user_data["waiting_for_check_photo"] = False

async def handle_label_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает фото для команды /label"""
    user_id = update.effective_user.id
    
    # Проверяем, что пользователь действительно ждёт анализа
    if not context.user_data.get("waiting_for_label_photo"):
        await update.message.reply_text(
            "Отправьте /label, чтобы проанализировать этикетку."
        )
        return
    
    # Получаем фото
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    await update.message.reply_text("🏷️ Анализирую этикетку...")
    
    # Здесь будет вызов Tesseract (позже)
    analysis = "🏷️ **Анализ этикетки**\n\nСостав: шерсть 80%, полиэстер 20%\n\n✅ Хорошее качество, можно брать!"
    
    await update.message.reply_text(analysis, parse_mode='Markdown')
    
    # Сбрасываем состояние
    context.user_data["waiting_for_label_photo"] = False

def get_item_analysis_stub():
    """Временная заглушка для анализа вещи"""
    return (
        "🧥 **Анализ вещи**\n\n"
        "✅ **БЕРИ, если:**\n"
        "• Вещь из натуральных материалов\n"
        "• Цвет нейтральный\n"
        "• Фасон классический\n\n"
        "❌ **НЕ БЕРИ, если:**\n"
        "• Есть крупные логотипы\n"
        "• Ткань синтетическая\n"
        "• У вас уже есть похожая\n\n"
        "💰 **Вердикт:** Инвестиционная покупка — ДА"
    )

async def subscribe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Создаём платёж на 599₽
    payment_url, payment_id = payment.create_payment(
        amount=599.00,
        description="Подписка «Стиль вне времени» — 1 месяц",
        telegram_id=user_id
    )
    
    # Сохраняем платёж в БД (свяжем с подпиской после подтверждения)
    database.save_payment(user_id, payment_id, 599.00, "pending")
    context.user_data["pending_payment_id"] = payment_id
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Оплатить 599₽", url=payment_url)],
        [InlineKeyboardButton("✅ Я оплатил(-а)", callback_data=f"check_subscription_{payment_id}")]
    ])
    
    await query.edit_message_text(
        "💳 Для оформления подписки нажмите на кнопку оплаты.\n\n"
        "После успешной оплаты нажмите «Я оплатил(-а)» — подписка активируется на 30 дней.",
        reply_markup=keyboard
    )

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    payment_id = query.data.split("_")[2]
    is_paid = payment.check_payment(payment_id)
    
    if is_paid:
        user_id = query.from_user.id
        database.update_payment_status(payment_id, "paid", datetime.now())
        database.create_subscription(user_id, payment_id)
        
        await query.edit_message_text(
            "✅ Оплата получена! Подписка активирована на 30 дней.\n\n"
            "Теперь вы можете отправлять неограниченное количество фото для анализа.\n"
            "Просто отправьте новый образ, и я сразу его разберу."
        )
    else:
        await query.edit_message_text(
            "❌ Платёж не найден. Пожалуйста, завершите оплату и нажмите кнопку снова.\n\n"
            "Если вы оплатили, но ошибка сохраняется — подождите 1-2 минуты (платёж может обрабатываться)."
        )
def get_current_ip():
    try:
        # Создаём подключение к DNS-серверу Google, чтобы узнать наш внешний IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "172.16.88.162"  # Ваш запасной IP из скриншота

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /check — анализ вещи: бери/не бери"""
    user_id = update.effective_user.id
    
    # Проверяем подписку
    has_subscription = database.has_active_subscription(user_id)
    has_free_left = database.has_free_consultation(user_id)
    
    if not has_subscription and not has_free_left:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📆 Оформить подписку 599₽/мес", callback_data="subscribe")]
        ])
        await update.message.reply_text(
            "🔍 Функция «Бери / Не бери» доступна только по подписке.\n\n"
            "Оформите подписку за 599₽ и получайте:\n"
            "✅ Анализ любых вещей перед покупкой\n"
            "✅ Советы по инвестиционным покупкам\n"
            "✅ Экономию на импульсивных тратах",
            reply_markup=keyboard
        )
        return
    
    # Устанавливаем режим ожидания фото для check
    context.user_data["waiting_for_check_photo"] = True
    
    await update.message.reply_text(
        "📸 Отправьте фото вещи, которую хотите проанализировать.\n\n"
        "Я скажу: ✅ БЕРИ или ❌ НЕ БЕРИ"
    )

async def label_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /label — анализ этикетки"""
    user_id = update.effective_user.id
    
    has_subscription = database.has_active_subscription(user_id)
    has_free_left = database.has_free_consultation(user_id)
    
    if not has_subscription and not has_free_left:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📆 Оформить подписку 599₽/мес", callback_data="subscribe")]
        ])
        await update.message.reply_text(
            "🏷️ Функция «Анализ этикетки» доступна только по подписке.\n\n"
            "Оформите подписку за 599₽ и получайте:\n"
            "✅ Анализ состава тканей\n"
            "✅ Оценку качества материалов",
            reply_markup=keyboard
        )
        return
    
    context.user_data["waiting_for_label_photo"] = True
    
    await update.message.reply_text(
        "🏷️ Отправьте фото этикетки (бирки) одежды.\n\n"
        "Я проанализирую состав и скажу, качественная ли вещь."
    )


def main():
    current_ip = get_current_ip()
    app = Application.builder().token(TOKEN).build()
    

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(subscribe_callback, pattern="subscribe"))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="check_subscription_"))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CommandHandler("label", handle_label))
    
    logging.info("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
        main()