from tortoise import Tortoise
from .config import DB_URL
from .models import Vendor, Consumer, Meal, Order, Metric
import logging

# Configure logging
logger = logging.getLogger(__name__)

async def init_db():
    """Initialize database connection and create tables if they don't exist."""
    logger.info(f"Initializing database with URL: {DB_URL}")
    await Tortoise.init(
        db_url=DB_URL,
        modules={"models": ["src.models"]}
    )
    # Tables will be created by Aerich migration or directly for testing
    if "sqlite" in DB_URL:  # For SQLite in-memory testing
        await Tortoise.generate_schemas()
    else:  # For production, we should always create schemas for safety
        await Tortoise.generate_schemas(safe=True)
    
    logger.info("Database connection initialized successfully.")


async def close_db():
    """Close database connection."""
    await Tortoise.close_connections()
    logger.info("Database connection closed.")
