import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import Message, User
from aiogram.fsm.context import FSMContext
from tortoise.contrib.test import initializer, finalizer

import os
import sys

# Mock environment variables before importing any app modules
os.environ["BOT_TOKEN"] = "test_token"
os.environ["ADMIN_CHAT_ID"] = "12345"
os.environ["PYTEST_CURRENT_TEST"] = "True"

# Mock the Bot class before it gets imported
with patch('aiogram.Bot') as MockBot:
    # Configure the mock to avoid token validation
    mock_bot_instance = MagicMock()
    MockBot.return_value = mock_bot_instance
    
    # Now import the app modules
    from src.bot import cmd_browse_meals
    from src.models import Vendor, VendorStatus, Meal, Consumer
    import datetime


@pytest.fixture(scope="module")
def event_loop():
    import asyncio
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def setup_db():
    await initializer()
    yield
    await finalizer()


@pytest.fixture
async def setup_test_data(setup_db):
    # Create test vendors
    vendor1 = await Vendor.create(
        telegram_id=12345,
        name="Test Vendor 1",
        contact_phone="+77771112233",
        status=VendorStatus.APPROVED
    )
    
    vendor2 = await Vendor.create(
        telegram_id=12346,
        name="Test Vendor 2",
        contact_phone="+77771112244",
        status=VendorStatus.APPROVED
    )
    
    # Create test consumer
    consumer = await Consumer.create(telegram_id=54321)
    
    # Create test meals
    now = datetime.datetime.now()
    pickup_start = now + datetime.timedelta(hours=2)
    pickup_end = now + datetime.timedelta(hours=3)
    
    # Create active meals
    meal1 = await Meal.create(
        name="Test Meal 1",
        description="Delicious test meal 1",
        price=1500.00,
        quantity=2,
        pickup_start_time=pickup_start,
        pickup_end_time=pickup_end,
        location_address="Test Address 1",
        location_latitude=43.25,
        location_longitude=76.95,
        is_active=True,
        vendor=vendor1
    )
    
    meal2 = await Meal.create(
        name="Test Meal 2",
        description="Delicious test meal 2",
        price=2000.50,
        quantity=3,
        pickup_start_time=pickup_start,
        pickup_end_time=pickup_end,
        location_address="Test Address 2",
        location_latitude=43.26,
        location_longitude=76.96,
        is_active=True,
        vendor=vendor2
    )
    
    # Create an inactive meal (should not be shown in browse)
    meal3 = await Meal.create(
        name="Inactive Meal",
        description="This meal should not appear in browse",
        price=1000.00,
        quantity=1,
        pickup_start_time=pickup_start,
        pickup_end_time=pickup_end,
        location_address="Test Address 3",
        location_latitude=43.27,
        location_longitude=76.97,
        is_active=False,
        vendor=vendor1
    )
    
    # Create a meal with zero quantity (should not be shown in browse)
    meal4 = await Meal.create(
        name="Zero Quantity Meal",
        description="This meal should not appear in browse",
        price=1200.00,
        quantity=0,
        pickup_start_time=pickup_start,
        pickup_end_time=pickup_end,
        location_address="Test Address 4",
        location_latitude=43.28,
        location_longitude=76.98,
        is_active=True,
        vendor=vendor2
    )
    
    return {
        "vendors": [vendor1, vendor2],
        "consumer": consumer,
        "meals": [meal1, meal2, meal3, meal4]
    }


@pytest.mark.asyncio
async def test_browse_meals_with_available_meals(setup_test_data):
    # Mock message
    message = AsyncMock(spec=Message)
    message.from_user = AsyncMock(spec=User)
    message.from_user.id = 54321  # Consumer ID from setup
    
    # Call the browse meals command
    await cmd_browse_meals(message)
    
    # Check that the correct message is sent
    assert message.answer.called
    
    # Get the first call arguments
    args = message.answer.call_args[0]
    message_text = args[0]
    
    # Check that the message contains both active meals
    assert "Test Meal 1" in message_text
    assert "1500" in message_text
    assert "Test Vendor 1" in message_text
    
    assert "Test Meal 2" in message_text
    assert "2000.5" in message_text
    assert "Test Vendor 2" in message_text
    
    # Check that inactive and zero quantity meals are not included
    assert "Inactive Meal" not in message_text
    assert "Zero Quantity Meal" not in message_text


@pytest.mark.asyncio
async def test_browse_meals_no_available_meals(setup_db):
    # Mock message
    message = AsyncMock(spec=Message)
    message.from_user = AsyncMock(spec=User)
    message.from_user.id = 54321
    
    # Call the browse meals command with no meals in DB
    await cmd_browse_meals(message)
    
    # Check that a "no meals available" message is sent
    message.answer.assert_called_once()
    
    # Get the first call arguments
    args = message.answer.call_args[0]
    message_text = args[0]
    
    # Check that the message indicates no meals available
    assert "нет доступных блюд" in message_text.lower() 