import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from .config import (
    BOT_TOKEN, WEBHOOK_MODE, WEBHOOK_URL, WEBHOOK_PATH, 
    WEBAPP_HOST, WEBAPP_PORT
)
from .db import init_db, close_db
from .bot import dp, bot, process_payment_webhook

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create web application for ASGI servers to use
app = web.Application()

# Setup webhook payment route
async def handle_payment_webhook(request):
    """
    Handle payment webhook requests from the payment gateway
    """
    try:
        # Get signature from header if available
        signature = request.headers.get('X-Signature', None)
        
        # Get JSON data from request
        webhook_data = await request.json()
        
        # Process the webhook
        success = await process_payment_webhook(webhook_data, signature)
        
        if success:
            return web.json_response({"status": "success"})
        else:
            return web.json_response({"status": "error", "message": "Failed to process webhook"}, status=400)
    
    except Exception as e:
        logger.error(f"Error processing payment webhook: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=400)


async def on_startup(bot: Bot, webhook_url: str = None):
    """Execute startup tasks"""
    # Initialize database connection
    await init_db()
    
    # Set webhook if in webhook mode
    if WEBHOOK_MODE and webhook_url:
        await bot.set_webhook(webhook_url)
        logger.info(f"Webhook set to: {webhook_url}")


async def on_shutdown(bot: Bot):
    """Execute shutdown tasks"""
    # Remove webhook if in webhook mode
    if WEBHOOK_MODE:
        await bot.delete_webhook()
        logger.info("Webhook removed")
    
    # Close database connection
    await close_db()


# Configure the app for ASGI
if WEBHOOK_MODE:
    # Setup webhook payment endpoint
    app.router.add_post('/payment-webhook', handle_payment_webhook)
    
    # Set up the webhook handler
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    # Set up startup and shutdown callbacks for the web app
    setup_application(app, dp, bot=bot)
    
    # Register startup callback
    app.on_startup.append(lambda app: on_startup(bot, WEBHOOK_URL))
    
    # Register shutdown callback
    app.on_shutdown.append(lambda app: on_shutdown(bot))


async def main():
    """Main function to run the bot"""
    # Set up dispatcher and include the webhook setup params
    dispatcher = dp
    
    try:
        if WEBHOOK_MODE:
            # Startup tasks
            await on_startup(bot, WEBHOOK_URL)
            
            # Start web application
            logger.info(f"Starting webhook on {WEBAPP_HOST}:{WEBAPP_PORT}")
            try:
                # Start web server
                web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
            finally:
                # Shutdown tasks
                await on_shutdown(bot)
        else:
            # Polling mode for local development
            # Startup tasks
            await on_startup(bot)
            
            try:
                # Start polling
                logger.info("Starting bot in polling mode")
                await dispatcher.start_polling(bot)
            finally:
                # Shutdown tasks
                await on_shutdown(bot)
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        # Ensure we close DB connection
        await close_db()


if __name__ == "__main__":
    """Entry point for the application"""
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!") 