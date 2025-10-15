from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extras import DictCursor
from contextlib import contextmanager
from config import PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DBNAME
import uuid
import logging


logger = logging.getLogger(__name__)

DSN = {
    "host": PG_HOST,
    "port": PG_PORT,
    "user": PG_USER,
    "password": PG_PASSWORD,
    "dbname": PG_DBNAME,
}


@contextmanager
def get_conn():
    """Контекстный менеджер для подключения к БД"""
    conn = psycopg2.connect(**DSN)
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Инициализация базы данных"""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Таблица пользователей
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
                
                # Таблица платежей
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
                logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise


def save_user(user_id: int, name: Optional[str] = None, contact: Optional[str] = None) -> None:
    """Сохраняет или обновляет пользователя"""
    try:
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
                logger.info(f"User {user_id} saved/updated")
    except Exception as e:
        logger.error(f"Error saving user {user_id}: {e}")
        raise


def set_payment(user_vk_id: int, payment_id: str, amount: float, currency: str = "RUB") -> None:
    """Создаёт платёж и связывает его с пользователем"""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO payments (payment_id, user_vk_id, amount, currency, status)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (payment_id) DO UPDATE SET status = EXCLUDED.status;
                """, (payment_id, user_vk_id, amount, currency, "created"))
                
                cur.execute("UPDATE users SET payment_id = %s WHERE user_id = %s;", 
                           (payment_id, user_vk_id))
                conn.commit()
                logger.info(f"Payment {payment_id} created for user {user_vk_id}")
    except Exception as e:
        logger.error(f"Error setting payment: {e}")
        raise


def mark_paid(payment_id: str) -> Optional[str]:
    """
    Отмечает платеж как успешный, генерирует уникальный токен и сохраняет его.
    Возвращает токен или None если платеж не найден.
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Обновляем статус платежа
                cur.execute("UPDATE payments SET status = %s WHERE payment_id = %s;", 
                           ("succeeded", payment_id))
                
                # Получаем user_vk_id по payment_id
                cur.execute("SELECT user_vk_id FROM payments WHERE payment_id = %s;", 
                           (payment_id,))
                result = cur.fetchone()
                
                if not result:
                    logger.warning(f"Payment {payment_id} not found")
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
                logger.info(f"User {user_vk_id} marked as paid, token generated: {token[:8]}...")
                return token
                
    except Exception as e:
        logger.error(f"Error marking payment as paid: {e}")
        raise


def is_user_paid(user_vk_id: int) -> bool:
    """Проверяет, оплатил ли пользователь"""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT is_paid FROM users WHERE user_id = %s;", (user_vk_id,))
                row = cur.fetchone()
                return bool(row and row["is_paid"])
    except Exception as e:
        logger.error(f"Error checking if user is paid: {e}")
        return False


def get_user_token(user_vk_id: int) -> Optional[str]:
    """Получает токен доступа конкретного пользователя"""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT token FROM users 
                    WHERE user_id = %s AND is_paid = TRUE AND token IS NOT NULL;
                """, (user_vk_id,))
                row = cur.fetchone()
                return row["token"] if row else None
    except Exception as e:
        logger.error(f"Error getting user token: {e}")
        return None


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Проверяет валидность токена доступа.
    Возвращает словарь с статусом проверки.
    """
    try:
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
                logger.info(f"Token verified for user {row['user_id']}")
                return {
                    "valid": True,
                    "message": "Доступ разрешён",
                    "user_id": row["user_id"]
                }
                
    except Exception as e:
        logger.error(f"Error verifying access token: {e}")
        return {
            "valid": False,
            "message": "Ошибка сервера",
            "user_id": None
        }


def renew_user_token(user_vk_id: int) -> Optional[str]:
    """
    Генерирует новый токен для пользователя (для продления доступа).
    Возвращает новый токен или None если пользователь не найден.
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                new_token = str(uuid.uuid4())
                cur.execute("""
                    UPDATE users 
                    SET token = %s, token_used = FALSE
                    WHERE user_id = %s AND is_paid = TRUE;
                """, (new_token, user_vk_id))
                conn.commit()
                
                if cur.rowcount > 0:
                    logger.info(f"New token generated for user {user_vk_id}")
                    return new_token
                return None
                
    except Exception as e:
        logger.error(f"Error renewing user token: {e}")
        return None


def revoke_access(user_vk_id: int) -> bool:
    """Отзывает доступ пользователя (блокирует токен)"""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users 
                    SET is_paid = FALSE, token = NULL, token_used = TRUE
                    WHERE user_id = %s;
                """, (user_vk_id,))
                conn.commit()
                logger.info(f"Access revoked for user {user_vk_id}")
                return cur.rowcount > 0
                
    except Exception as e:
        logger.error(f"Error revoking access: {e}")
        return False


def get_access_info(user_vk_id: int) -> Dict[str, Any]:
    """Получает полную информацию о доступе пользователя"""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        is_paid,
                        token,
                        token_used,
                        paid_at,
                        contact,
                        created_at
                    FROM users 
                    WHERE user_id = %s;
                """, (user_vk_id,))
                row = cur.fetchone()
                
                if not row:
                    return {"error": "Пользователь не найден"}
                
                return {
                    "is_paid": row["is_paid"],
                    "has_token": row["token"] is not None,
                    "token_used": row["token_used"],
                    "paid_at": row["paid_at"],
                    "contact": row["contact"],
                    "created_at": row["created_at"]
                }
                
    except Exception as e:
        logger.error(f"Error getting access info: {e}")
        return {"error": str(e)}


def get_payment_stats() -> Dict[str, Any]:
    """Получает статистику платежей"""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_users,
                        SUM(CASE WHEN is_paid THEN 1 ELSE 0 END) as paid_users,
                        SUM(CASE WHEN token_used THEN 1 ELSE 0 END) as accessed_users
                    FROM users;
                """)
                users_stat = cur.fetchone()
                
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_payments,
                        SUM(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END) as succeeded,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                        SUM(CASE WHEN status = 'created' THEN 1 ELSE 0 END) as pending,
                        SUM(amount) as total_amount
                    FROM payments;
                """)
                payment_stat = cur.fetchone()
                
                return {
                    "users": dict(users_stat),
                    "payments": dict(payment_stat)
                }
                
    except Exception as e:
        logger.error(f"Error getting payment stats: {e}")
        return {
            "users": {},
            "payments": {}
        }
