import asyncio
import time
from tortoise import Tortoise
from .config import DB_URL
from .models import Vendor, Consumer, Meal, Order, Metric
import logging
import subprocess
import sys
import os

# Configure logging
logger = logging.getLogger(__name__)

async def run_migrations():
    """Run database migrations using aerich"""
    try:
        logger.info("Running database migrations...")
        
        # Check if migrations directory exists
        if not os.path.exists("migrations"):
            logger.info("Initializing aerich...")
            result = subprocess.run([
                sys.executable, "-m", "aerich", "init", 
                "-t", "src.config.TORTOISE_ORM"
            ], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to initialize aerich: {result.stderr}")
                return False
        
        # Check if models migration exists
        if not os.path.exists("migrations/models"):
            logger.info("Creating initial migration...")
            result = subprocess.run([
                sys.executable, "-m", "aerich", "init-db"
            ], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to create initial migration: {result.stderr}")
                return False
        
        # Run migrations
        logger.info("Applying migrations...")
        result = subprocess.run([
            sys.executable, "-m", "aerich", "upgrade"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Migrations completed successfully")
            return True
        else:
            logger.error(f"Migration failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        return False

async def init_db_with_retry(max_retries=5, retry_delay=5):
    """Initialize database connection with retry logic"""
    for attempt in range(max_retries):
        try:
            logger.info(f"Initializing database (attempt {attempt + 1}/{max_retries}) with URL: {DB_URL}")
            
            # Add connection timeout and retry parameters to DB_URL
            db_url = DB_URL
            if "postgres://" in db_url and "?" not in db_url:
                db_url += "?command_timeout=30&server_settings={}&retries=3"
            elif "postgres://" in db_url:
                db_url += "&command_timeout=30&retries=3"
            
            await Tortoise.init(
                db_url=db_url,
                modules={"models": ["src.models"]}
            )
            
            # Tables will be created by Aerich migration or directly for testing
            if "sqlite" in DB_URL:  # For SQLite in-memory testing
                await Tortoise.generate_schemas()
            else:  # For production, we should always create schemas for safety
                await Tortoise.generate_schemas(safe=True)
            
            logger.info("Database connection initialized successfully.")
            return True
            
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("All database connection attempts failed")
                raise

async def init_db():
    """Initialize database connection and run migrations."""
    # Try to connect to the database with retry logic
    await init_db_with_retry()
    
    # Run migrations after successful connection (only for non-testing environments)
    if "sqlite" not in DB_URL:
        migration_success = await run_migrations()
        if not migration_success:
            logger.warning("Migrations failed, but continuing with startup")

async def close_db():
    """Close database connection."""
    await Tortoise.close_connections()
    logger.info("Database connection closed.")
