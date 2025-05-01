import pytest
import pytest_asyncio
import os
from tortoise import Tortoise
from src.db import init_db, close_db
from src.config import TESTING

# Ensure we're in testing mode
os.environ["PYTEST_CURRENT_TEST"] = "yes"

@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_tests_db():
    """Initialize test database before running tests and clean up after"""
    await init_db()
    
    # Make sure all models are registered for the tests
    from src.models import Vendor, Consumer, Meal, Order
    
    yield
    
    # Clean up after tests
    await close_db()

@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db():
    """Clean database before each test"""
    conn = Tortoise.get_connection("default")
    
    # Only run if we're using in-memory SQLite (for testing)
    if TESTING:
        await conn.execute_script("DELETE FROM orders")
        await conn.execute_script("DELETE FROM meals")
        await conn.execute_script("DELETE FROM vendors")
        await conn.execute_script("DELETE FROM consumers")
    
    yield 