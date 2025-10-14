from dotenv import load_dotenv
import os

load_dotenv()

VK_GROUP_TOKEN = os.getenv("VK_GROUP_TOKEN")
VK_CONFIRMATION_TOKEN = os.getenv("VK_CONFIRMATION_TOKEN")

YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

BASE_URL = os.getenv("BASE_URL", "https://example.com")
PRIVATE_GROUP_URL = os.getenv("PRIVATE_GROUP_URL", "")

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", 5432))
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_DBNAME = os.getenv("PG_DBNAME")

FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
