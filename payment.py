import builtins
str = builtins.str
import uuid
import logging
import os
from dotenv import load_dotenv
from yookassa import Configuration, Payment

# Загружаем .env ПРИНУДИТЕЛЬНО с указанием пути
from pathlib import Path
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Правильные имена переменных (как в .env)
SHOP_ID = os.getenv("YUKASSA_SHOP_ID")
SECRET_KEY = os.getenv("YUKASSA_SECRET_KEY")

# ДИАГНОСТИКА (удалите после проверки)
print("=" * 50)
print("ПРОВЕРКА КЛЮЧЕЙ ЮKASSA:")
print(f"  SHOP_ID из .env: {SHOP_ID}")
print(f"  SECRET_KEY из .env: {SECRET_KEY[:20] if SECRET_KEY else 'None'}...")
print(f"  Тип SHOP_ID: {type(SHOP_ID)}")
print(f"  Тип SECRET_KEY: {type(SECRET_KEY)}")
print("=" * 50)

# Настройка ЮKassa
if SHOP_ID and SECRET_KEY:
    Configuration.configure(account_id=SHOP_ID, secret_key=SECRET_KEY)
    logging.info("✅ ЮKassa настроена успешно")
else:
    logging.error("❌ ЮKassa ключи не найдены в .env!")
    logging.error("   Проверьте, что в .env есть:")
    logging.error("   YUKASSA_SHOP_ID=1325221")
    logging.error("   YUKASSA_SECRET_KEY=live_...")

def create_payment(amount: float, description: str, telegram_id: int, return_url: str = None) -> tuple:
    """Создаёт платёж в ЮKassa."""
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
        
        logging.info(f"✅ Создан платёж {payment_id} на сумму {amount} руб.")
        
        return payment_url, payment_id
        
    except Exception as e:
        logging.error(f"❌ Ошибка при создании платежа: {e}")
        raise

def check_payment(payment_id: str) -> bool:
    """Проверяет статус платежа."""
    try:
        payment = Payment.find_one(payment_id)
        return payment.status == "succeeded" and payment.paid == True
    except Exception as e:
        logging.error(f"❌ Ошибка при проверке платежа: {e}")
        return False