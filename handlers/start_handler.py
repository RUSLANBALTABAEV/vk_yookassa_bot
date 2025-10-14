import json
from typing import Dict
from utils.vk_api_wrapper import VKBot
from utils.db import save_user
from pathlib import Path

MESSAGES = json.load(open(Path(__file__).parent.parent / "static" / "messages.json", encoding="utf-8"))


def handle(event: Dict) -> None:
    """
    Обработчик события message_new: собирает имя и контакт.
    Простой state-machine: если пользователь написал 'купить' — запрашиваем e-mail.
    """
    obj = event.get("object", {}).get("message", {})
    text = obj.get("text", "").strip().lower()
    from_id = obj.get("from_id")
    if not from_id:
        return

    # простая логика: если написал 'начать' или 'привет' — приветствие
    if text in ("начать", "привет", "/start"):
        VKBot.send_message(from_id, MESSAGES.get("welcome"))
        return

    # если написал 'купить' — переключаемся на обработчик оплаты
    if text == "купить":
        VKBot.send_message(from_id, MESSAGES.get("ask_contact"))
        # сохраняем запись о пользователе (в дальнейшем обработчик payment соберёт контакт)
        save_user(from_id)
