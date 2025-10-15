from flask import Flask, request, jsonify
from utils.db import init_db, verify_access_token
from utils.vk_api_wrapper import VKBot
from handlers import start_handler, payment_handler, access_handler
from config import FLASK_HOST, FLASK_PORT, VK_CONFIRMATION_TOKEN, PRIVATE_GROUP_URL
import logging

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Инициализация базы
try:
    init_db()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Database initialization failed: {e}")

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
    try:
        data = request.get_json()
        if not data:
            logger.warning("Empty callback data received")
            return "no data", 400

        t = data.get("type")
        logger.info(f"VK callback received: type={t}")
        
        if t == "confirmation":
            logger.info("VK confirmation token sent")
            return VK_CONFIRMATION_TOKEN

        if t == "message_new":
            # Делегируем обработку с передачей экземпляра vkbot
            vkbot.handle_event(data, vkbot)
            return "ok", 200
            
        return "ok", 200
        
    except Exception as e:
        logger.error(f"VK callback error: {e}", exc_info=True)
        return "error", 500


@app.route("/yookassa_webhook", methods=["POST"])
def yookassa_webhook():
    """
    Принимаем webhook от YooKassa.
    """
    try:
        payload = request.get_json()
        if not payload:
            logger.warning("Empty webhook payload received")
            return "error", 400

        logger.info(f"YooKassa webhook: event={payload.get('event')}")
        
        from utils.yookassa_api import process_webhook_event
        process_webhook_event(payload, vkbot)
        
        logger.info("Webhook processed successfully")
        return jsonify({"status": "ok"}), 200
        
    except Exception as exc:
        logger.error(f"Webhook processing error: {exc}", exc_info=True)
        return jsonify({"error": str(exc)}), 500


@app.route("/access", methods=["GET"])
def access_link():
    """
    Отправляет HTML страницу для проверки токена.
    Когда пользователь переходит по ссылке с токеном.
    """
    try:
        with open('templates/access.html', encoding='utf-8') as f:
            return f.read(), 200, {'Content-Type': 'text/html; charset=utf-8'}
    except Exception as e:
        logger.error(f"Access page error: {e}")
        return "Error loading page", 500


@app.route("/verify-token", methods=["GET"])
def verify_token():
    """
    API эндпоинт для проверки токена доступа (AJAX запрос).
    """
    try:
        token = request.args.get("token")
        
        if not token:
            logger.warning("Token verification: no token provided")
            return jsonify({"valid": False, "message": "Токен не предоставлен"}), 400
        
        logger.info(f"Token verification attempt: {token[:8]}...")
        result = verify_access_token(token)
        
        if result["valid"]:
            logger.info(f"Token verified successfully for user {result['user_id']}")
            return jsonify(result), 200
        else:
            logger.warning(f"Token verification failed: {result['message']}")
            return jsonify(result), 403
            
    except Exception as e:
        logger.error(f"Token verification error: {e}", exc_info=True)
        return jsonify({"valid": False, "message": "Ошибка сервера"}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint для мониторинга.
    """
    try:
        from utils.db import get_payment_stats
        stats = get_payment_stats()
        return jsonify({
            "status": "ok",
            "stats": stats
        }), 200
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """Обработка 404 ошибок"""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Обработка 500 ошибок"""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("VK Payment Bot starting...")
    logger.info(f"Host: {FLASK_HOST}, Port: {FLASK_PORT}")
    logger.info("=" * 50)
    
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False)
