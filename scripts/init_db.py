import asyncio
import logging
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from src.config import DB_URL
from src.models import Consumer, Vendor, Meal, Order, Metric

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_db():
    try:
        # Connect to the database
        logger.info(f"Initializing database connection to {DB_URL}")
        await Tortoise.init(
            db_url=DB_URL,
            modules={"models": ["src.models"]}
        )
        
        # Generate the schema
        logger.info("Creating database schema")
        await Tortoise.generate_schemas(safe=True)
        
        # Verify tables were created
        conn = Tortoise.get_connection("default")
        
        # List of expected tables
        expected_tables = ["consumers", "vendors", "meals", "orders", "metrics"]
        
        # Check each table
        for table in expected_tables:
            try:
                await conn.execute_query(f"SELECT COUNT(*) FROM {table}")
                logger.info(f"Table '{table}' exists and is accessible")
            except Exception as e:
                logger.error(f"Table '{table}' check failed: {e}")
                raise
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        # Close connection
        await Tortoise.close_connections()

if __name__ == "__main__":
    try:
        asyncio.run(init_db())
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1) 