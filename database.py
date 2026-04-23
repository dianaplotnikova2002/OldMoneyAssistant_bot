import sqlite3
from datetime import datetime, timedelta

def init_db():
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    
    # Пользователи
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Подписки
    c.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            telegram_id INTEGER PRIMARY KEY,
            is_active BOOLEAN DEFAULT 0,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            auto_renew BOOLEAN DEFAULT 0,
            payment_id TEXT,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        )
    """)
    
    # Консультации
    c.execute("""
        CREATE TABLE IF NOT EXISTS consultations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            photo_file_id TEXT,
            analysis_result TEXT,
            is_free BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Платежи (НОВАЯ ТАБЛИЦА)
    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            payment_id TEXT UNIQUE,
            amount REAL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        )
    """)
    
    conn.commit()
    conn.close()

def save_user(telegram_id, username, first_name, last_name):
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO users (telegram_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
    """, (telegram_id, username, first_name, last_name))
    conn.commit()
    conn.close()

def has_free_consultation(telegram_id) -> bool:
    """Проверяет, использовал ли пользователь бесплатную консультацию."""
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM consultations 
        WHERE telegram_id = ? AND is_free = 1
    """, (telegram_id,))
    count = c.fetchone()[0]
    conn.close()
    return count == 0

def save_consultation(telegram_id, photo_file_id, analysis_result, is_free=True):
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO consultations (telegram_id, photo_file_id, analysis_result, is_free)
        VALUES (?, ?, ?, ?)
    """, (telegram_id, photo_file_id, analysis_result, is_free))
    conn.commit()
    conn.close()

def has_active_subscription(telegram_id) -> bool:
    """Проверяет, активна ли подписка у пользователя."""
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("""
        SELECT is_active, end_date FROM subscriptions 
        WHERE telegram_id = ?
    """, (telegram_id,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        return False
    
    is_active, end_date = result
    if end_date:
        end_date = datetime.fromisoformat(end_date)
        if end_date < datetime.now():
            return False
    
    return bool(is_active)

def create_subscription(telegram_id, payment_id):
    """Создаёт подписку на 30 дней."""
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    start_date = datetime.now()
    end_date = start_date + timedelta(days=30)
    
    c.execute("""
        INSERT OR REPLACE INTO subscriptions 
        (telegram_id, is_active, start_date, end_date, payment_id, auto_renew)
        VALUES (?, 1, ?, ?, ?, 0)
    """, (telegram_id, start_date.isoformat(), end_date.isoformat(), payment_id))
    
    conn.commit()
    conn.close()

def get_subscription_info(telegram_id):
    """Возвращает информацию о подписке."""
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("""
        SELECT is_active, start_date, end_date FROM subscriptions 
        WHERE telegram_id = ?
    """, (telegram_id,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        return {"active": False}
    
    is_active, start_date, end_date = result
    return {
        "active": bool(is_active),
        "start_date": start_date,
        "end_date": end_date
    }

def save_payment(telegram_id, payment_id, amount, status="pending"):
    """Сохраняет информацию о платеже."""
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO payments (telegram_id, payment_id, amount, status)
        VALUES (?, ?, ?, ?)
    """, (telegram_id, payment_id, amount, status))
    conn.commit()
    conn.close()

def update_payment_status(payment_id, status, paid_at=None):
    """Обновляет статус платежа."""
    conn = sqlite3.connect("bot_database.db")
    c = conn.cursor()
    if paid_at:
        c.execute("""
            UPDATE payments SET status = ?, paid_at = ? WHERE payment_id = ?
        """, (status, paid_at, payment_id))
    else:
        c.execute("""
            UPDATE payments SET status = ? WHERE payment_id = ?
        """, (status, payment_id))
    conn.commit()
    conn.close()