import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import aiohttp_cors
import ssl

from .config import (
    BOT_TOKEN, WEBHOOK_MODE, WEBHOOK_URL, WEBHOOK_PATH, 
    WEBAPP_HOST, WEBAPP_PORT, SSL_CERT_PATH, SSL_KEY_PATH, USE_SSL
)
from .db import init_db, close_db
from .bot import dp, bot, process_payment_webhook
from .security import webhook_security_middleware, start_security_tasks, rate_limiter

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


async def on_startup(app=None):
    """Execute startup tasks"""
    # Initialize database connection
    await init_db()
    
    # Start security background tasks
    await start_security_tasks()
    
    # Set webhook if in webhook mode
    if WEBHOOK_MODE and WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL)
        logger.info(f"Webhook set to: {WEBHOOK_URL}")


async def on_shutdown(app=None):
    """Execute shutdown tasks"""
    # Remove webhook if in webhook mode
    if WEBHOOK_MODE:
        await bot.delete_webhook()
        logger.info("Webhook removed")
    
    # Close database connection
    await close_db()


# Apply security middleware to the application
@web.middleware
async def security_middleware(request, handler):
    return await webhook_security_middleware(request, handler)
    
app.middlewares.append(security_middleware)

# Health check endpoint
async def health_check(request):
    """Simple health check endpoint for monitoring"""
    return web.json_response({"status": "ok"})
    
app.router.add_get('/health', health_check)

# Configure the app for ASGI
if WEBHOOK_MODE:
    # Set up CORS for security
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            max_age=3600,
            allow_methods=["POST"]
        )
    })
    
    # Setup webhook payment endpoint
    # Apply CORS to payment webhook endpoint
    resource = cors.add(app.router.add_post('/payment-webhook', handle_payment_webhook))
    
    # Set up the webhook handler
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    # Set up startup and shutdown callbacks for the web app
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)


async def main():
    """Main function to run the bot"""
    try:
        if WEBHOOK_MODE:
            # Start web application
            logger.info(f"Starting webhook on {WEBAPP_HOST}:{WEBAPP_PORT}")
            
            # SSL configuration for secure webhook
            ssl_context = None
            if USE_SSL and SSL_CERT_PATH and SSL_KEY_PATH:
                ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                ssl_context.load_cert_chain(SSL_CERT_PATH, SSL_KEY_PATH)
                logger.info("SSL enabled for webhook server")
            
            # Use runner to properly handle application lifecycle
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host=WEBAPP_HOST, port=int(WEBAPP_PORT), ssl_context=ssl_context)
            
            await site.start()
            
            # Keep the server running
            while True:
                await asyncio.sleep(3600)  # Sleep for 1 hour
                
        else:
            # Polling mode for local development
            # Startup tasks
            await on_startup()
            
            try:
                # Start polling
                logger.info("Starting bot in polling mode")
                await dp.start_polling(bot)
            finally:
                # Shutdown tasks
                await on_shutdown()
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