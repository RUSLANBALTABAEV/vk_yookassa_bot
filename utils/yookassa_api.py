# utils/yookassa_api.py

import os
import uuid
import hmac
import hashlib
from typing import Dict, Any
from yookassa import Configuration, Payment
from flask import Flask, request, jsonify
from utils.db import set_payment, mark_paid
from utils.vk_api_wrapper import VKBot

# Конфигурация из .env
Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

BASE_URL = os.getenv("BASE_URL", "https://example.com")
PRIVATE_GROUP_URL = os.getenv("PRIVATE_GROUP_URL", "https://vk.com/club233286501")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

app = Flask(__name__)


# === 1️⃣ Создание платежа ===
def create_payment_for_user(user_vk_id: int, amount: float) -> Dict[str, Any]:
    """
    Создаёт платёж в YooKassa, сохраняет его в БД и возвращает ссылку.
    """
    idempotence_key = uuid.uuid4().hex
    payment = Payment.create({
        "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
        "confirmation": {
            "type": "redirect",
            "return_url": f"{BASE_URL}/"
        },
        "capture": True,
        "description": f"Оплата материалов от пользователя {user_vk_id}",
        "metadata": {"user_vk_id": str(user_vk_id)}
    }, idempotence_key)

    payment_id = payment.id
    confirmation_url = payment.confirmation.confirmation_url

    # Сохраняем информацию в PostgreSQL
    set_payment(user_vk_id, payment_id, amount, "RUB")

    return {"payment_id": payment_id, "url": confirmation_url}


# === 2️⃣ Проверка подписи ===
def verify_signature(secret: str, data: bytes, header: str) -> bool:
    """
    Проверка подлинности webhook-запроса от YooKassa (HMAC SHA256).
    """
    if not header:
        return False
    digest = hmac.new(secret.encode(), msg=data, digestmod=hashlib.sha256).hexdigest()
    if header.startswith("sha256="):
        header = header.split("=", 1)[1]
    return hmac.compare_digest(digest, header)


# === 3️⃣ Обработка успешной оплаты ===
def process_payment_success(payment_id: str, user_vk_id: str):
    """
    Отмечает платёж как оплаченный и уведомляет пользователя.
    """
    mark_paid(payment_id)
    vk = VKBot()
    vk.send_message(
        int(user_vk_id),
        "✅ Оплата подтверждена! 🎉 Доступ к материалам открыт."
    )
    vk.send_message(
        int(user_vk_id),
        f"📚 Перейдите по ссылке: {PRIVATE_GROUP_URL}"
    )


# === 4️⃣ Webhook от YooKassa ===
@app.route("/yookassa/webhook", methods=["POST"])
def webhook():
    """
    Обработка уведомлений от YooKassa о статусе платежей.
    """
    raw_data = request.data
    signature = request.headers.get("X-Request-Signature-SHA256")

    # Проверка подписи
    if not verify_signature(YOOKASSA_SECRET_KEY, raw_data, signature):
        print("❌ Подпись не прошла проверку. Запрос отклонён.")
        return jsonify({"status": "forbidden"}), 403

    data = request.json
    event = data.get("event")

    if event == "payment.succeeded":
        payment_obj = data.get("object", {})
        payment_id = payment_obj.get("id")
        metadata = payment_obj.get("metadata", {})
        user_vk_id = metadata.get("user_vk_id")

        print(f"✅ Платёж {payment_id} успешно завершён пользователем {user_vk_id}")
        process_payment_success(payment_id, user_vk_id)

    else:
        print(f"⚠️ Получено событие {event}, не 'payment.succeeded'")

    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("🚀 Запуск локального Flask-сервера для приёма webhook от YooKassa...")
    app.run(host="0.0.0.0", port=int(os.getenv("FLASK_PORT", 5000)))
