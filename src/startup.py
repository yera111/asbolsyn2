import asyncio
import logging
import os
import sys
from tortoise import Tortoise
from .config import DB_URL

logger = logging.getLogger(__name__)

async def wait_for_database(max_attempts=30, delay=2):
    """Wait for database to be ready with connection testing"""
    for attempt in range(max_attempts):
        try:
            logger.info(f"Testing database connection (attempt {attempt + 1}/{max_attempts})")
            
            # Create a simple test connection
            from .config import TORTOISE_ORM
            await Tortoise.init(config=TORTOISE_ORM)
            await Tortoise.close_connections()
            
            logger.info("Database connection successful!")
            return True
            
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_attempts - 1:
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                logger.error("All database connection attempts failed")
                return False
    
    return False

async def ensure_database_ready():
    """Ensure database is ready before starting the application"""
    logger.info("Ensuring database is ready...")
    
    # Wait for database to be available
    if not await wait_for_database():
        logger.error("Database is not available, cannot start application")
        sys.exit(1)
    
    logger.info("Database is ready, proceeding with application startup")

def run_startup():
    """Run startup checks (synchronous wrapper)"""
    asyncio.run(ensure_database_ready()) 