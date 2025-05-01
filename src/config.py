import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Check if running in pytest
TESTING = "PYTEST_CURRENT_TEST" in os.environ

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "test_token" if TESTING else None)
if not BOT_TOKEN and not TESTING:
    raise ValueError("BOT_TOKEN environment variable is not set!")

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "asbolsyn_test" if TESTING else "asbolsyn")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Admin configuration
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "12345" if TESTING else None)

# Database URL for Tortoise ORM
DATABASE_URL = f"postgres://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
if TESTING:
    # Use SQLite in-memory for testing
    DATABASE_URL = "sqlite://:memory:"

# Default language
DEFAULT_LANGUAGE = "ru"

# Payment Gateway configuration (for testing initially)
PAYMENT_GATEWAY_ENABLED = os.getenv("PAYMENT_GATEWAY_ENABLED", "True").lower() in ["true", "1", "yes"]
PAYMENT_GATEWAY_API_KEY = os.getenv("PAYMENT_GATEWAY_API_KEY", "test_api_key" if TESTING else None)
PAYMENT_GATEWAY_SECRET = os.getenv("PAYMENT_GATEWAY_SECRET", "test_secret" if TESTING else None)
PAYMENT_GATEWAY_URL = os.getenv("PAYMENT_GATEWAY_URL", "https://test-payment.kz" if TESTING else None)
PAYMENT_WEBHOOK_SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET", "webhook_secret" if TESTING else None)
PAYMENT_SUCCESS_URL = os.getenv("PAYMENT_SUCCESS_URL", "https://t.me/as_bolsyn_bot" if TESTING else None)
PAYMENT_FAILURE_URL = os.getenv("PAYMENT_FAILURE_URL", "https://t.me/as_bolsyn_bot" if TESTING else None)
