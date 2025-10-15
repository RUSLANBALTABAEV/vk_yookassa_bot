from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extras import DictCursor
from contextlib import contextmanager
from config import PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DBNAME
import uuid

DSN = {
    "host": PG_HOST,
    "port": PG_PORT,
    "user": PG_USER,
    "password": PG_PASSWORD,
    "dbname": PG_DBNAME,
}


@contextmanager
def get_conn():
    conn = psycopg2.connect(**DSN)
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE NOT NULL,
                    name TEXT,
                    contact TEXT,
                    payment_id TEXT,
                    is_paid BOOLEAN DEFAULT FALSE,
                    token TEXT UNIQUE,
                    token_used BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    paid_at TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    payment_id TEXT UNIQUE,
                    user_vk_id BIGINT,
                    amount NUMERIC(10,2),
                    currency TEXT,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()


def save_user(user_id: int, name: Optional[str] = None, contact: Optional[str] = None) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (user_id, name, contact)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                  SET name = COALESCE(EXCLUDED.name, users.name),
                      contact = COALESCE(EXCLUDED.contact, users.contact);
            """, (user_id, name, contact))
            conn.commit()


def set_payment(user_vk_id: int, payment_id: str, amount: float, currency: str = "RUB") -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO payments (payment_id, user_vk_id, amount, currency, status)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (payment_id) DO UPDATE SET status = EXCLUDED.status;
            """, (payment_id, user_vk_id, amount, currency, "created"))
            cur.execute("UPDATE users SET payment_id = %s WHERE user_id = %s;", (payment_id, user_vk_id))
            conn.commit()


def mark_paid(payment_id: str) -> str:
    """
    Отмечает платеж как успешный, генерирует уникальный токен и сохраняет его.
    Возвращает токен.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Обновляем статус платежа
            cur.execute("UPDATE payments SET status = %s WHERE payment_id = %s;", ("succeeded", payment_id))
            
            # Получаем user_vk_id по payment_id
            cur.execute("SELECT user_vk_id FROM payments WHERE payment_id = %s;", (payment_id,))
            result = cur.fetchone()
            
            if not result:
                conn.commit()
                return None
            
            user_vk_id = result[0]
            
            # Генерируем уникальный токен
            token = str(uuid.uuid4())
            
            # Обновляем пользователя: отмечаем оплачено, сохраняем токен, время оплаты
            cur.execute("""
                UPDATE users 
                SET is_paid = TRUE, token = %s, paid_at = CURRENT_TIMESTAMP
                WHERE user_id = %s;
            """, (token, user_vk_id))
            
            conn.commit()
            return token


def is_user_paid(user_vk_id: int) -> bool:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT is_paid FROM users WHERE user_id = %s;", (user_vk_id,))
            row = cur.fetchone()
            return bool(row and row["is_paid"])


def get_user_token(user_vk_id: int) -> Optional[str]:
    """
    Получает токен доступа конкретного пользователя.
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""
                SELECT token FROM users 
                WHERE user_id = %s AND is_paid = TRUE AND token IS NOT NULL;
            """, (user_vk_id,))
            row = cur.fetchone()
            return row["token"] if row else None


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Проверяет валидность токена доступа.
    Возвращает словарь с статусом проверки.
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""
                SELECT user_id, is_paid, token_used FROM users 
                WHERE token = %s;
            """, (token,))
            row = cur.fetchone()
            
            # Токен не существует
            if not row:
                return {
                    "valid": False,
                    "message": "Токен не найден или истёк",
                    "user_id": None
                }
            
            # Пользователь не оплатил
            if not row["is_paid"]:
                return {
                    "valid": False,
                    "message": "Оплата не найдена",
                    "user_id": row["user_id"]
                }
            
            # Токен уже использован
            if row["token_used"]:
                return {
                    "valid": False,
                    "message": "Токен уже был использован",
                    "user_id": row["user_id"]
                }
            
            # Отмечаем токен как использованный
            cur.execute("""
                UPDATE users SET token_used = TRUE 
                WHERE token = %s;
            """, (token,))
            conn.commit()
            
            # Токен валиден
            return {
                "valid": True,
                "message": "Доступ разрешён",
                "user_id": row["user_id"]
            }
