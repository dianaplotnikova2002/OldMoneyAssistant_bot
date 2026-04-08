import socket
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
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
    user_id = update.effective_user.id
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    # Сохраняем фото для последующего анализа
    context.user_data["last_photo_bytes"] = photo_bytes
    context.user_data["last_photo_id"] = update.message.photo[-1].file_id
    
    # Проверяем подписку
    has_subscription = database.has_active_subscription(user_id)
    has_free_left = database.has_free_consultation(user_id)
    
    # Случай 1: есть активная подписка → сразу анализ
    if has_subscription:
        await update.message.reply_text("🔍 Анализирую ваш образ (подписка активна)...")
        analysis = await analyzer.analyze_photo(photo_bytes)
        database.save_consultation(user_id, update.message.photo[-1].file_id, analysis, is_free=False)
        await update.message.reply_text(analysis)
        return
    
    # Случай 2: нет подписки, но есть бесплатная консультация
    if has_free_left:
        await update.message.reply_text(
            "🎁 Это ваша БЕСПЛАТНАЯ консультация!\n"
            "🔍 Анализирую образ..."
        )
        analysis = await analyzer.analyze_photo(photo_bytes)
        database.save_consultation(user_id, update.message.photo[-1].file_id, analysis, is_free=True)
        await update.message.reply_text(analysis)
        
        # После бесплатной консультации предлагаем подписку
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📆 Оформить подписку 599₽/мес", callback_data="subscribe")]
        ])
        await update.message.reply_text(
            "✨ Понравился разбор?\n\n"
            "Оформите подписку за 599₽ и получайте неограниченные консультации в течение месяца.\n\n"
            "С подпиской вы сможете:\n"
            "✅ Разбирать любые образы\n"
            "✅ Получать советы по улучшению\n"
            "✅ Стать ближе к эстетике Old Money",
            reply_markup=keyboard
        )
        return
    
    # Случай 3: нет подписки, бесплатная уже использована
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📆 Оформить подписку 599₽/мес", callback_data="subscribe")]
    ])
    await update.message.reply_text(
        "❌ У вас нет активной подписки, а бесплатная консультация уже использована.\n\n"
        "Оформите подписку за 599₽ и продолжайте получать разборы образов.",
        reply_markup=keyboard
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

def main():
    current_ip = get_current_ip()
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(subscribe_callback, pattern="subscribe"))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="check_subscription_"))
    app.add_handler(CommandHandler("label", handle_label))
    
    logging.info("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
        main()