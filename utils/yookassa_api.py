import uuid
import hmac
import hashlib
from typing import Dict, Any
from yookassa import Configuration, Payment
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, BASE_URL
from utils.db import set_payment, mark_paid
from utils.vk_api_wrapper import VKBot

# Настройка официального SDK
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY


def create_payment_for_user(user_vk_id: int, amount: float) -> Dict[str, Any]:
    """
    Создаёт платёж в YooKassa и возвращает confirmation_url и payment.id.
    """
    idempotence_key = uuid.uuid4().hex
    payment = Payment.create({
        "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": f"{BASE_URL}/"},
        "capture": True,
        "description": f"Оплата материалов user {user_vk_id}",
        "metadata": {"user_vk_id": str(user_vk_id)}
    }, idempotence_key)

    payment_id = payment.id
    confirmation_url = payment.confirmation.confirmation_url
    # сохраняем привязку в БД
    set_payment(user_vk_id, payment_id, amount, "RUB")
    return {"payment_id": payment_id, "url": confirmation_url}


def verify_signature(secret: str, data: bytes, header: str) -> bool:
    """
    Проверка подписи YooKassa (HMAC SHA256).
    В header можно получить подпись из 'X-Request-Signature-SHA256' или схожего.
    """
    digest = hmac.new(secret.encode(), msg=data, digestmod=hashlib.sha256).hexdigest()
    # header sometimes contains 'sha256=...' or raw signature
    if header is None:
        return False
    if header.startswith("sha256="):
        header = header.split("=", 1)[1]
    return hmac.compare_digest(digest, header)


def process_webhook_event(payload: Dict[str, Any]) -> None:
    """
    Обрабатывает JSON webhook от YooKassa.
    Ожидаем структуру: {'event': 'payment.succeeded', 'object': {...}}
    """
    event = payload.get("event")
    obj = payload.get("object", {})
    if not obj:
        return

    status = obj.get("status")
    payment_id = obj.get("id")
    metadata = obj.get("metadata", {})
    user_vk = metadata.get("user_vk_id")
    if status == "succeeded":
        # Обновляем БД
        mark_paid(payment_id)
        # Отправляем пользователю сообщение
        if user_vk:
            try:
                VKBot.send_message(int(user_vk), "✅ Оплата подтверждена! Доступ к материалам:")
                VKBot.send_message(int(user_vk), f"{BASE_URL}")
            except Exception as exc:
                print("Error sending VK message:", exc)
