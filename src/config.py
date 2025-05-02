import os
from dotenv import load_dotenv
import pytz

# Load environment variables from .env file
load_dotenv()

# Check if running in pytest
TESTING = "PYTEST_CURRENT_TEST" in os.environ

# Webhook mode (True for production, False for local polling)
WEBHOOK_MODE = os.getenv("WEBHOOK_MODE", "False").lower() in ["true", "1", "yes"]
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://your-app-name.onrender.com")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")  # for listen on all interfaces
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", os.getenv("PORT", "8000")))  # Default port that most PaaS use

# SSL Configuration for secure webhook
USE_SSL = os.getenv("USE_SSL", "False").lower() in ["true", "1", "yes"]
SSL_CERT_PATH = os.getenv("SSL_CERT_PATH", "")
SSL_KEY_PATH = os.getenv("SSL_KEY_PATH", "")

# Security Configuration
RATE_LIMIT_GENERAL = int(os.getenv("RATE_LIMIT_GENERAL", "20"))  # Requests per minute
RATE_LIMIT_REGISTER = int(os.getenv("RATE_LIMIT_REGISTER", "2"))  # Registration attempts per minute
RATE_LIMIT_ADD_MEAL = int(os.getenv("RATE_LIMIT_ADD_MEAL", "5"))  # Meal additions per minute
RATE_LIMIT_PAYMENT = int(os.getenv("RATE_LIMIT_PAYMENT", "3"))  # Payment attempts per minute
WEBHOOK_RATE_LIMIT = int(os.getenv("WEBHOOK_RATE_LIMIT", "30"))  # Webhook requests per 10 seconds

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

# Timezone configuration
ALMATY_TIMEZONE = pytz.timezone("Asia/Almaty")
TIMEZONE_OFFSET_HOURS = 6  # Almaty is UTC+6

# Payment Gateway configuration (for testing initially)
PAYMENT_GATEWAY_ENABLED = os.getenv("PAYMENT_GATEWAY_ENABLED", "True").lower() in ["true", "1", "yes"]
PAYMENT_GATEWAY_API_KEY = os.getenv("PAYMENT_GATEWAY_API_KEY", "test_api_key" if TESTING else "demo_key")
PAYMENT_GATEWAY_SECRET = os.getenv("PAYMENT_GATEWAY_SECRET", "test_secret" if TESTING else "demo_secret")
PAYMENT_GATEWAY_URL = os.getenv("PAYMENT_GATEWAY_URL", "https://test-payment.kz" if TESTING else "https://example.com")
PAYMENT_WEBHOOK_SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET", "webhook_secret" if TESTING else "demo_webhook_secret")
PAYMENT_SUCCESS_URL = os.getenv("PAYMENT_SUCCESS_URL", "https://t.me/as_bolsyn_bot")
PAYMENT_FAILURE_URL = os.getenv("PAYMENT_FAILURE_URL", "https://t.me/as_bolsyn_bot")
