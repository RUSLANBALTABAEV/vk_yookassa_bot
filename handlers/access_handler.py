from typing import Dict
from utils.db import is_user_paid, get_user_token
from config import BASE_URL
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
    Обработчик для команды 'доступ': если пользователь оплачен, даём уникальную ссылку с токеном.
    """
    obj = event.get("object", {}).get("message", {})
    text = obj.get("text", "").strip().lower()
    from_id = obj.get("from_id")
    
    if not from_id:
        return

    try:
        if text == "доступ":
            if is_user_paid(from_id):
                token = get_user_token(from_id)
                if token:
                    # Генерируем уникальную ссылку с токеном
                    access_url = f"{BASE_URL}/access?token={token}"
                    # Оборачиваем в VK away.php для безопасности
                    vk_away_url = f"https://vk.com/away.php?to={access_url}"
                    
                    access_msg = MESSAGES.get("access_granted", 
                        "✅ Ваша личная ссылка:\n{url}").format(url=vk_away_url)
                    vkbot.send_message(from_id, access_msg)
                    logger.info(f"Access link sent to user {from_id}")
                else:
                    vkbot.send_message(from_id, MESSAGES.get("no_token", 
                        "❌ Токен доступа не найден. Повторите попытку позже."))
                    logger.warning(f"No token found for paid user {from_id}")
            else:
                vkbot.send_message(from_id, MESSAGES.get("no_access", 
                    "❌ У вас нет доступа. Для получения доступа напишите 'купить'."))
                logger.info(f"User {from_id} requested access without payment")
                
    except Exception as e:
        logger.error(f"Error in access_handler for user {from_id}: {e}")
        vkbot.send_message(from_id, "❌ Произошла ошибка. Попробуйте позже.")
