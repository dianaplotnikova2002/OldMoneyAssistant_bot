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
import analyzer

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

database.init_db()


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
        "/status — статус вашей подписки\n"
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
    
    # Проверяем режимы
    if context.user_data.get("waiting_for_check_photo"):
        await handle_check_photo(update, context)
        return
    
    if context.user_data.get("waiting_for_label_photo"):
        await handle_label_photo(update, context)
        return
    
    # Проверка подписки
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
    
    await update.message.reply_text("🔍 Анализирую ваш образ...")
    
    if has_free_left and not has_subscription:
        analysis = await analyze_outfit(photo_bytes)
        database.save_consultation(user_id, update.message.photo[-1].file_id, analysis, is_free=True)
        await update.message.reply_text(analysis)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📆 Оформить подписку 599₽/мес", callback_data="subscribe")]
        ])
        await update.message.reply_text(
            "✨ Понравился разбор?\n\n"
            "Оформите подписку за 599₽ и получайте неограниченные консультации.",
            reply_markup=keyboard
        )
    else:
        analysis = await analyze_outfit(photo_bytes)
        database.save_consultation(user_id, update.message.photo[-1].file_id, analysis, is_free=False)
        await update.message.reply_text(analysis)

async def handle_check_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает фото для команды /check"""
    if not context.user_data.get("waiting_for_check_photo"):
        await update.message.reply_text(
            "Отправьте /check, чтобы проанализировать вещь, или просто фото для разбора образа."
        )
        return
    
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    await update.message.reply_text("🔍 Анализирую вещь... Это займёт несколько секунд.")
    
    analysis = await analyze_item_for_purchase(photo_bytes)
    
    await update.message.reply_text(analysis)
    context.user_data["waiting_for_check_photo"] = False

async def handle_label_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает фото для команды /label"""
    if not context.user_data.get("waiting_for_label_photo"):
        await update.message.reply_text(
            "Отправьте /label, чтобы проанализировать этикетку."
        )
        return
    
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    await update.message.reply_text("🏷️ Анализирую этикетку...")
    
    analysis = await analyze_label(photo_bytes)
    
    await update.message.reply_text(analysis, parse_mode='Markdown')
    context.user_data["waiting_for_label_photo"] = False
# Добавьте ЭТУ функцию для теста

async def test_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    print(f"🔵 ЛЮБОЙ callback получен! data={query.data}")
    await query.answer(text="Тест работает!", show_alert=True)

# В функции main() добавьте ЭТУ строку ПЕРЕД другими обработчиками
def main():
    app = Application.builder().token(TOKEN).build()
    
    # Временный тестовый обработчик - поймает любой callback
    app.add_handler(CallbackQueryHandler(test_callback))  # <- без pattern, ловит всё
    
    # Остальные ваши обработчики
    app.add_handler(CommandHandler("start", start))
    # ... все остальные
    
    app.run_polling()

async def subscribe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Проверка на InvalidCallbackData
    if isinstance(query.data, InvalidCallbackData):
        await query.answer(text="Кнопка устарела. Пожалуйста, запросите новую подписку заново.", show_alert=True)
        return
    
    await query.answer()
    
    user_id = query.from_user.id
    
    try:
        # Логируем для отладки
        logging.info(f"Создаём платёж для user_id={user_id}")
        
        # Создаём платёж на 599₽
        payment_url, payment_id = payment.create_payment(
            amount=599.00,
            description="Подписка «Стиль вне времени» — 1 месяц",
            telegram_id=user_id
        )
        
        logging.info(f"Платёж создан: {payment_id}")
        
        # Сохраняем платёж в БД
        database.save_payment(user_id, payment_id, 599.00, "pending")
        context.user_data["pending_payment_id"] = payment_id
        
        # Создаём кнопки
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Оплатить 599₽", url=payment_url)],
            [InlineKeyboardButton("✅ Я оплатил(-а)", callback_data=f"check_subscription_{payment_id}")]
        ])
        
        # Редактируем сообщение с кнопками
        await query.edit_message_text(
            "💳 Для оформления подписки нажмите на кнопку оплаты.\n\n"
            "После успешной оплаты нажмите «Я оплатил(-а)» — подписка активируется на 30 дней.",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logging.error(f"Ошибка при создании платежа: {e}", exc_info=True)
        await query.edit_message_text(
            f"❌ Произошла ошибка при создании платежа.\n\n"
            f"Пожалуйста, попробуйте позже или обратитесь к администратору.\n\n"
            f"Ошибка: {str(e)}"
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

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /check — анализ вещи: бери/не бери"""
    user_id = update.effective_user.id
    
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
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CommandHandler("label", label_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(subscribe_callback, pattern="subscribe"))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="check_subscription_"))
    
    logging.info("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()