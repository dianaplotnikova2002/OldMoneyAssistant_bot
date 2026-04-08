import uuid

def create_payment(amount: float, description: str, telegram_id: int):
    """Временная заглушка для оплаты."""
    payment_id = str(uuid.uuid4())
    # Временная тестовая ссылка
    test_url = "https://yookassa.ru/test_payment"
    return test_url, payment_id

def check_payment(payment_id: str) -> bool:
    """Временная заглушка — всегда возвращает True для теста."""
    return True

def save_payment(telegram_id, payment_id, amount, status):
    """Заглушка для сохранения платежа."""
    pass

def update_payment_status(payment_id, status, paid_at=None):
    """Заглушка для обновления статуса."""
    pass