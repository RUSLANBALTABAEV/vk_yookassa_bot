from flask import Flask, request, jsonify
from utils.db import init_db
from utils.vk_api_wrapper import VKBot
from handlers import start_handler, payment_handler, access_handler
from config import FLASK_HOST, FLASK_PORT, VK_CONFIRMATION_TOKEN

app = Flask(__name__)

# Инициализация базы
init_db()

# Инициализация обёртки VK
vkbot = VKBot()

# Регистрация хэндлеров (логика обработки message_new)
vkbot.register_handler(start_handler.handle)
vkbot.register_handler(payment_handler.handle)
vkbot.register_handler(access_handler.handle)


@app.route("/vk_callback", methods=["POST"])
def vk_callback():
    """
    Точка входа для VK Callback API.
    При подключении VK присылает type == 'confirmation' — возвращаем VK_CONFIRMATION_TOKEN.
    При новых сообщениях — передаём объект в vkbot для обработки.
    """
    data = request.get_json()
    if not data:
        return "no data", 400

    t = data.get("type")
    if t == "confirmation":
        return VK_CONFIRMATION_TOKEN

    if t == "message_new":
        # Делегируем обработку
        vkbot.handle_event(data)
    return "ok", 200


@app.route("/yookassa_webhook", methods=["POST"])
def yookassa_webhook():
    """
    Принимаем webhook от YooKassa.
    """
    payload = request.get_json()
    # Простейшая обработка: /utils/yookassa_api.py выполняет валидацию подписи
    from utils.yookassa_api import process_webhook_event
    try:
        process_webhook_event(payload)
    except Exception as exc:
        # в продакшене: логировать
        print("Webhook processing error:", exc)
        return "error", 500
    return jsonify({}), 200


if __name__ == "__main__":
    print("VK bot started")
    app.run(host=FLASK_HOST, port=FLASK_PORT)
