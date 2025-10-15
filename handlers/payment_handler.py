from typing import Dict
from utils.yookassa_api import create_payment_for_user
from utils.db import save_user, is_user_paid
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


def handle(event: Dict, vkbot) -> None:
    """
    Обработчик, который реагирует когда пользователь присылает свой контакт или команды.
    Если текст похож на email — начинаем оплату.
    Если команда 'статус' — проверяем статус оплаты.
    """
    obj = event.get("object", {}).get("message", {})
    text = obj.get("text", "").strip()
    from_id = obj.get("from_id")
    
    if not from_id:
        return

    try:
        # Если текст похож на email
        if "@" in text and "." in text:
            save_user(from_id, contact=text)
            logger.info(f"Email received from user {from_id}: {text}")
            
            try:
                # Создаём платёж (фиксированная сумма)
                res = create_payment_for_user(from_id, 499.00)
                payment_link = MESSAGES.get("payment_text", "Оплатите по ссылке: {url}").format(url=res["url"])
                vkbot.send_message(from_id, payment_link)
                logger.info(f"Payment link sent to user {from_id}")
                
            except Exception as e:
                logger.error(f"Error creating payment for user {from_id}: {e}")
                vkbot.send_message(from_id, MESSAGES.get("payment_error", 
                    "❌ Ошибка при создании платежа. Попробуйте позже."))
            return

        # Если написал 'статус' — проверяем
        if text.lower() == "статус":
            paid = is_user_paid(from_id)
            if paid:
                vkbot.send_message(from_id, MESSAGES.get("already_paid", 
                    "✅ У вас уже есть доступ!"))
                logger.info(f"User {from_id} checked status: paid")
            else:
                vkbot.send_message(from_id, MESSAGES.get("not_paid", 
                    "❌ Оплата не найдена. Напишите 'купить'."))
                logger.info(f"User {from_id} checked status: not paid")
                
    except Exception as e:
        logger.error(f"Error in payment_handler for user {from_id}: {e}")
        vkbot.send_message(from_id, "❌ Произошла ошибка. Попробуйте позже.")
