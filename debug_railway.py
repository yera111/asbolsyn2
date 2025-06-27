#!/usr/bin/env python3
"""
Debug script for Railway deployment issues
Run this to test database connectivity and identify migration issues
"""

import os
import sys
import asyncio
import logging
from src.config import DB_URL, DB_HOST, DB_PORT, DB_NAME, DB_USER

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_environment():
    """Check environment variables"""
    logger.info("=== Environment Check ===")
    
    # Check key environment variables
    env_vars = ['DATABASE_URL', 'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    for var in env_vars:
        value = os.getenv(var, 'NOT SET')
        if 'PASSWORD' in var and value != 'NOT SET':
            value = '*' * len(value)  # Hide password
        logger.info(f"{var}: {value}")
    
    logger.info(f"Constructed DB_URL: {DB_URL.replace(os.getenv('DB_PASSWORD', ''), '***')}")
    
    # Check if we're in Railway environment
    railway_env = os.getenv('RAILWAY_ENVIRONMENT_NAME', 'NOT SET')
    logger.info(f"Railway Environment: {railway_env}")

async def test_database_connection():
    """Test database connection with detailed error reporting"""
    logger.info("=== Database Connection Test ===")
    
    try:
        from tortoise import Tortoise
        
        # Test basic connection
        logger.info("Attempting to connect to database...")
        await Tortoise.init(
            db_url=DB_URL,
            modules={"models": ["src.models"]}
        )
        
        # Test a simple query
        logger.info("Testing database query...")
        connection = Tortoise.get_connection("default")
        result = await connection.execute_query("SELECT 1")
        logger.info(f"Query result: {result}")
        
        await Tortoise.close_connections()
        logger.info("✅ Database connection successful!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        return False

def check_migration_files():
    """Check migration files and aerich status"""
    logger.info("=== Migration Files Check ===")
    
    # Check if migrations directory exists
    if os.path.exists("migrations"):
        logger.info("✅ migrations/ directory exists")
        
        # Check models directory
        if os.path.exists("migrations/models"):
            logger.info("✅ migrations/models/ directory exists")
            
            # List migration files
            try:
                migration_files = os.listdir("migrations/models")
                logger.info(f"Migration files: {migration_files}")
            except Exception as e:
                logger.error(f"Error reading migration files: {e}")
        else:
            logger.warning("❌ migrations/models/ directory does not exist")
    else:
        logger.warning("❌ migrations/ directory does not exist")
    
    # Check pyproject.toml
    if os.path.exists("pyproject.toml"):
        logger.info("✅ pyproject.toml exists")
        try:
            with open("pyproject.toml", "r") as f:
                content = f.read()
                if "[tool.aerich]" in content:
                    logger.info("✅ Aerich configuration found in pyproject.toml")
                else:
                    logger.warning("❌ No aerich configuration in pyproject.toml")
        except Exception as e:
            logger.error(f"Error reading pyproject.toml: {e}")

async def main():
    """Main debug function"""
    logger.info("Starting Railway deployment debug...")
    
    check_environment()
    check_migration_files()
    await test_database_connection()
    
    logger.info("Debug completed.")

if __name__ == "__main__":
    asyncio.run(main()) 