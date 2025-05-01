from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from .config import DATABASE_URL
from .models import Vendor, Consumer, Meal, Order, Metric


async def init_db():
    """Initialize database connection and create tables if they don't exist."""
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={"models": ["src.models"]}
    )
    await Tortoise.generate_schemas()
    
    # Basic migration: Check if quantity column exists in orders table
    # and add it if it's missing
    try:
        conn = Tortoise.get_connection("default")
        # Check if quantity column exists in orders table
        result = await conn.execute_query("SELECT column_name FROM information_schema.columns WHERE table_name='orders' AND column_name='quantity'")
        if not result[1]:  # Column doesn't exist
            print("Adding 'quantity' column to orders table...")
            await conn.execute_script("ALTER TABLE orders ADD COLUMN quantity INTEGER DEFAULT 1")
    except OperationalError as e:
        # Table might not exist yet, which is fine - it will be created with the schema
        print(f"Migration check: {e}")

    print("Database connection initialized successfully.")


async def close_db():
    """Close database connection."""
    await Tortoise.close_connections()
    print("Database connection closed.")
