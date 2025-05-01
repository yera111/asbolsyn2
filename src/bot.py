import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import Message

from .config import BOT_TOKEN
from .db import init_db, close_db
from .models import Consumer

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Russian text templates
TEXT = {
    "welcome": "Добро пожаловать в As Bolsyn! Этот бот поможет вам найти и приобрести блюда от местных заведений по сниженным ценам.",
    "help": "Доступные команды:\n/start - Запустить бот\n/help - Показать эту справку",
}


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Handler for /start command"""
    # Register user if not already registered
    user_id = message.from_user.id
    consumer, created = await Consumer.get_or_create(telegram_id=user_id)
    
    await message.answer(TEXT["welcome"])


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Handler for /help command"""
    await message.answer(TEXT["help"])


async def main():
    """Main function to run the bot"""
    # Initialize database connection
    await init_db()
    
    try:
        # Start the bot
        await dp.start_polling(bot)
    finally:
        # Close database connection when done
        await close_db()


if __name__ == "__main__":
    """Entry point for the application"""
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")
