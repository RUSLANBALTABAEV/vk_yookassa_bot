from dotenv import load_dotenv
import os

# Загружаем переменные из .env файла
load_dotenv()

# VK API Configuration
VK_GROUP_TOKEN = os.getenv("VK_GROUP_TOKEN")
VK_CONFIRMATION_TOKEN = os.getenv("VK_CONFIRMATION_TOKEN")

# YooKassa Configuration
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

# Server Configuration
BASE_URL = os.getenv("BASE_URL", "https://example.com")
PRIVATE_GROUP_URL = os.getenv("PRIVATE_GROUP_URL", "")

# PostgreSQL Configuration
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", 5432))
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")
PG_DBNAME = os.getenv("PG_DBNAME", "vk_bot_db")

# Flask Configuration
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))

# Validation
def validate_config():
    """Проверяет, что все необходимые переменные установлены"""
    required_vars = [
        ("VK_GROUP_TOKEN", VK_GROUP_TOKEN),
        ("VK_CONFIRMATION_TOKEN", VK_CONFIRMATION_TOKEN),
        ("YOOKASSA_SHOP_ID", YOOKASSA_SHOP_ID),
        ("YOOKASSA_SECRET_KEY", YOOKASSA_SECRET_KEY),
        ("BASE_URL", BASE_URL),
        ("PG_USER", PG_USER),
        ("PG_PASSWORD", PG_PASSWORD),
    ]
    
    missing = [name for name, value in required_vars if not value]
    
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

# Запускаем валидацию при импорте
try:
    validate_config()
except ValueError as e:
    print(f"⚠️  Warning: {e}")
    print("   Please set environment variables in .env file")
