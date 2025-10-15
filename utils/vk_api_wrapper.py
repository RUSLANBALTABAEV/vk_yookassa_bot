import requests
import uuid
from config import VK_GROUP_TOKEN
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

API_URL = "https://api.vk.com/method/"
API_VERSION = "5.131"


class VKBot:
    """
    Обёртка для VK Callback API.
    Регистрирует обработчики, принимает события и вызывает их по очереди.
    """

    def __init__(self):
        self.token = VK_GROUP_TOKEN
        self.handlers = []

    def register_handler(self, func):
        """
        Регистрирует функцию-обработчик. Функция должна принимать параметры event и vkbot.
        """
        self.handlers.append(func)
        logger.info(f"Handler registered: {func.__name__}")

    def handle_event(self, data: Dict[str, Any], vkbot) -> None:
        """
        Делегирует событие всем зарегистрированным хэндлерам.
        Каждый хэндлер решает, нужно ли ему обрабатывать событие.
        """
        for handler in self.handlers:
            try:
                handler(data, vkbot)
            except Exception as exc:
                logger.error(f"Handler error in {handler.__name__}: {exc}", exc_info=True)

    def send_message(self, user_id: int, text: str) -> Dict[str, Any]:
        """
        Отправляет сообщение пользователю через VK API.
        """
        try:
            params = {
                "user_id": user_id,
                "message": text,
                "random_id": uuid.uuid4().int >> 64,
                "access_token": self.token,
                "v": API_VERSION
            }
            response = requests.post(API_URL + "messages.send", params=params, timeout=10)
            result = response.json()
            
            if "error" in result:
                logger.error(f"VK API error: {result['error']}")
                return {}
            
            logger.info(f"Message sent to user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error sending message to {user_id}: {e}")
            return {}
