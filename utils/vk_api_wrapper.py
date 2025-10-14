import requests
import uuid
from config import VK_GROUP_TOKEN
from typing import Dict, Any

API_URL = "https://api.vk.com/method/"
API_VERSION = "5.131"


class VKBot:
    """
    Минимальная обёртка для VK Callback API.
    Регистрирует обработчики (функции), принимает событие и вызывает их по очереди.
    """

    def __init__(self):
        self.token = VK_GROUP_TOKEN
        self.handlers = []

    def register_handler(self, func):
        """
        Регистрирует функцию-обработчик. Функция должна принимать параметр event (dict).
        """
        self.handlers.append(func)

    def handle_event(self, data: Dict[str, Any]) -> None:
        """
        Делегирует событие всем зарегистрированным хэндлерам.
        Каждый хэндлер решает, нужно ли ему обрабатывать событие.
        """
        for handler in self.handlers:
            try:
                handler(data)
            except Exception as exc:
                # В продакшене логировать
                print("Handler error:", exc)

    @staticmethod
    def send_message(user_id: int, text: str) -> None:
        params = {
            "user_id": user_id,
            "message": text,
            "random_id": uuid.uuid4().int >> 64,
            "access_token": VK_GROUP_TOKEN,
            "v": API_VERSION
        }
        requests.post(API_URL + "messages.send", params=params)
