from tortoise import Tortoise
from .config import DATABASE_URL


async def init_db():
    """Initialize database connection and create tables if they don't exist."""
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={"models": ["src.models"]}
    )
    await Tortoise.generate_schemas()
    
    print("Database connection initialized successfully.")


async def close_db():
    """Close database connection."""
    await Tortoise.close_connections()
    print("Database connection closed.")
