from typing import Dict
from utils.vk_api_wrapper import VKBot
from utils.db import is_user_paid
from config import PRIVATE_GROUP_URL


def handle(event: Dict) -> None:
    """
    Простой обработчик для команды 'доступ': если пользователь оплачен, даём ссылку на группу.
    """
    obj = event.get("object", {}).get("message", {})
    text = obj.get("text", "").strip().lower()
    from_id = obj.get("from_id")
    if not from_id:
        return

    if text == "доступ":
        if is_user_paid(from_id):
            VKBot.send_message(from_id, f"✅ Вам открыт доступ: {PRIVATE_GROUP_URL}")
        else:
            VKBot.send_message(from_id, "❌ У вас нет доступа. Для получения доступа напишите 'купить'.")
