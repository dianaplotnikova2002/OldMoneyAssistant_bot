import uuid
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from yookassa import Configuration, Payment
from telegram.ext import InvalidCallbackData
load_dotenv()

# Настройка ЮKassa
SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

if SHOP_ID and SECRET_KEY:
    Configuration.account_id = SHOP_ID
    Configuration.secret_key = SECRET_KEY
    logging.info("ЮKassa настроена успешно")
else:
    logging.warning("ЮKassa ключи не настроены. Платежи не будут работать.")


def create_payment(amount: float, description: str, telegram_id: int, return_url: str = None) -> tuple:
    """
    Создаёт платёж в ЮKassa.
    
    Args:
        amount: Сумма платежа (например, 599.00)
        description: Описание платежа
        telegram_id: ID пользователя в Telegram
        return_url: URL для возврата после оплаты (опционально)
    
    Returns:
        tuple: (payment_url, payment_id)
    """
    try:
        idempotence_key = str(uuid.uuid4())
        
        payment_params = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url or "https://t.me/OldMoneyAssistant_bot"
            },
            "capture": True,
            "description": description,
            "metadata": {
                "telegram_id": str(telegram_id),
                "payment_type": "subscription"
            }
        }
        
        payment = Payment.create(payment_params, idempotence_key)
        
        payment_url = payment.confirmation.confirmation_url
        payment_id = payment.id
        
        logging.info(f"Создан платёж {payment_id} на сумму {amount} руб.")
        
        return payment_url, payment_id
        
    except Exception as e:
        logging.error(f"Ошибка при создании платежа: {e}")
        raise

def check_payment(payment_id: str) -> bool:
    """
    Проверяет статус платежа в ЮKassa.
    
    Args:
        payment_id: ID платежа
    
    Returns:
        bool: True если платёж успешен, иначе False
    """
    try:
        payment = Payment.find_one(payment_id)
        
        status = payment.status
        paid = payment.paid
        
        logging.info(f"Платёж {payment_id}: статус={status}, paid={paid}")
        
        return status == "succeeded" and paid == True
        
    except Exception as e:
        logging.error(f"Ошибка при проверке платежа {payment_id}: {e}")
        return False