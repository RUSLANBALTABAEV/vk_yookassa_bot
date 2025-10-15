import json
from typing import Dict
from utils.db import save_user
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
    Обработчик события message_new: приветствие и сбор контакта.
    Если пользователь написал 'купить' — запрашиваем e-mail.
    """
    obj = event.get("object", {}).get("message", {})
    text = obj.get("text", "").strip().lower()
    from_id = obj.get("from_id")
    
    if not from_id:
        return

    try:
        # Простая логика: если написал 'начать' или 'привет' — приветствие
        if text in ("начать", "привет", "/start"):
            vkbot.send_message(from_id, MESSAGES.get("welcome", "Привет!"))
            save_user(from_id)
            logger.info(f"Welcome message sent to user {from_id}")
            return

        # если написал 'купить' — переключаемся на обработчик оплаты
        if text == "купить":
            vkbot.send_message(from_id, MESSAGES.get("ask_contact", "Пришлите ваш email"))
            save_user(from_id)
            logger.info(f"Purchase request from user {from_id}")
            
    except Exception as e:
        logger.error(f"Error in start_handler for user {from_id}: {e}")
        vkbot.send_message(from_id, "❌ Произошла ошибка. Попробуйте позже.")
