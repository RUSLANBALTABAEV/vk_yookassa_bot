import uuid
from typing import Dict, Any
from yookassa import Configuration, Payment
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, BASE_URL
from utils.db import set_payment, mark_paid
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Загружаем сообщения
try:
    MESSAGES = json.load(open(Path(__file__).parent.parent / "static" / "messages.json", encoding="utf-8"))
except Exception as e:
    logger.error(f"Error loading messages: {e}")
    MESSAGES = {}

# Настройка официального SDK
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY


def create_payment_for_user(user_vk_id: int, amount: float) -> Dict[str, Any]:
    """
    Создаёт платёж в YooKassa и возвращает confirmation_url и payment.id.
    """
    try:
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
        
        # Сохраняем привязку в БД
        set_payment(user_vk_id, payment_id, amount, "RUB")
        
        logger.info(f"Payment created: {payment_id}, amount: {amount}, user: {user_vk_id}")
        
        return {
            "payment_id": payment_id,
            "url": confirmation_url
        }
        
    except Exception as e:
        logger.error(f"Error creating payment for user {user_vk_id}: {e}")
        raise


def process_webhook_event(payload: Dict[str, Any], vkbot) -> None:
    """
    Обрабатывает JSON webhook от YooKassa.
    Ожидаем структуру: {'event': 'payment.succeeded', 'object': {...}}
    После успешной оплаты отправляет пользователю подтверждение и уникальную ссылку с токеном.
    """
    try:
        event = payload.get("event")
        obj = payload.get("object", {})
        
        if not obj:
            logger.warning("Empty webhook object")
            return

        status = obj.get("status")
        payment_id = obj.get("id")
        metadata = obj.get("metadata", {})
        user_vk = metadata.get("user_vk_id")
        
        logger.info(f"Webhook event: {event}, status: {status}, payment: {payment_id}")
        
        if status == "succeeded" and payment_id:
            # Обновляем БД — отмечаем, что оплата прошла и генерируем токен
            token = mark_paid(payment_id)
            
            # Отправляем пользователю сообщение с подтверждением
            if user_vk and token:
                try:
                    # Сообщение подтверждения
                    confirmation_msg = MESSAGES.get("payment_confirmed", "✅ Оплата подтверждена!")
                    vkbot.send_message(int(user_vk), confirmation_msg)
                    
                    # Генерируем уникальную ссылку с токеном
                    access_url = f"{BASE_URL}/access?token={token}"
                    # Оборачиваем в VK away.php для безопасности
                    vk_away_url = f"https://vk.com/away.php?to={access_url}"
                    
                    access_msg = MESSAGES.get("access_ready", 
                        "✅ Доступ открыт!\n\n🔗 Ваша личная ссылка:\n{url}").format(url=vk_away_url)
                    vkbot.send_message(int(user_vk), access_msg)
                    
                    logger.info(f"Access link sent to user {user_vk}")
                    
                except Exception as exc:
                    logger.error(f"Error sending VK message to {user_vk}: {exc}")
        
        elif status == "canceled":
            logger.info(f"Payment {payment_id} canceled")
            if user_vk:
                try:
                    vkbot.send_message(int(user_vk), "⏸️ Платеж отменён")
                except Exception as exc:
                    logger.error(f"Error sending cancel message: {exc}")
        
        elif status == "failed":
            logger.warning(f"Payment {payment_id} failed")
            if user_vk:
                try:
                    vkbot.send_message(int(user_vk), 
                        "❌ Платеж не прошёл. Попробуйте ещё раз, написав 'купить'")
                except Exception as exc:
                    logger.error(f"Error sending fail message: {exc}")
                    
    except Exception as e:
        logger.error(f"Error processing webhook event: {e}", exc_info=True)
