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
