from typing import Dict
from utils.vk_api_wrapper import VKBot
from utils.yookassa_api import create_payment_for_user
from utils.db import save_user
import json
from pathlib import Path

MESSAGES = json.load(open(Path(__file__).parent.parent / "static" / "messages.json", encoding="utf-8"))


def handle(event: Dict) -> None:
    """
    Обработчик, который реагирует когда пользователь присылает свой контакт или 'оплатить'.
    Для простоты: если пользователь прислал текст, содержащий '@' — считаем это email и начинаем оплату.
    """
    obj = event.get("object", {}).get("message", {})
    text = obj.get("text", "").strip()
    from_id = obj.get("from_id")
    if not from_id:
        return

    # Если текст похож на email (упрощённо)
    if "@" in text and "." in text:
        save_user(from_id, contact=text)
        # создаём платёж (фиксированная сумма, например 499)
        res = create_payment_for_user(from_id, 499.00)
        VKBot.send_message(from_id, MESSAGES.get("payment_text").format(url=res["url"]))
        return

    # Если написал 'статус' — проверяем
    if text.lower() == "статус":
        from utils.db import is_user_paid
        paid = is_user_paid(from_id)
        if paid:
            VKBot.send_message(from_id, MESSAGES.get("already_paid"))
        else:
            VKBot.send_message(from_id, MESSAGES.get("not_paid"))
