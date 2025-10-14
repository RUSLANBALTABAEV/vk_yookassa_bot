from typing import Optional
import psycopg2
from psycopg2.extras import DictCursor
from contextlib import contextmanager
from config import PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DBNAME

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
                    token TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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


def mark_paid(payment_id: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE payments SET status = %s WHERE payment_id = %s;", ("succeeded", payment_id))
            cur.execute("UPDATE users SET is_paid = TRUE WHERE payment_id = %s;", (payment_id,))
            conn.commit()


def is_user_paid(user_vk_id: int) -> bool:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT is_paid FROM users WHERE user_id = %s;", (user_vk_id,))
            row = cur.fetchone()
            return bool(row and row["is_paid"])
