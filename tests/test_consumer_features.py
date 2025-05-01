import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import Message, User, Location, CallbackQuery
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
    from src.bot import cmd_meals_nearby, process_meals_nearby, calculate_distance, filter_meals_by_distance, cmd_view_meal, process_buy_callback, TEXT
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
    
    # Meal in Almaty city center
    meal1 = await Meal.create(
        name="Test Meal 1",
        description="Delicious test meal 1",
        price=1500.00,
        quantity=2,
        pickup_start_time=pickup_start,
        pickup_end_time=pickup_end,
        location_address="Test Address 1",
        location_latitude=43.238949,  # Almaty coordinates
        location_longitude=76.889709,
        is_active=True,
        vendor=vendor1
    )
    
    # Meal in Almaty outskirts
    meal2 = await Meal.create(
        name="Test Meal 2",
        description="Delicious test meal 2",
        price=2000.50,
        quantity=3,
        pickup_start_time=pickup_start,
        pickup_end_time=pickup_end,
        location_address="Test Address 2",
        location_latitude=43.346065,  # ~12km from city center
        location_longitude=77.005005,
        is_active=True,
        vendor=vendor2
    )
    
    # Meal far from Almaty (in Astana)
    meal3 = await Meal.create(
        name="Far Away Meal",
        description="This meal should not appear in nearby search",
        price=1000.00,
        quantity=1,
        pickup_start_time=pickup_start,
        pickup_end_time=pickup_end,
        location_address="Test Address 3",
        location_latitude=51.128207,  # Astana coordinates
        location_longitude=71.430420,
        is_active=True,
        vendor=vendor1
    )
    
    # Inactive meal
    meal4 = await Meal.create(
        name="Inactive Meal",
        description="This meal should not appear in results",
        price=1200.00,
        quantity=2,
        pickup_start_time=pickup_start,
        pickup_end_time=pickup_end,
        location_address="Test Address 4",
        location_latitude=43.238949,
        location_longitude=76.889709,
        is_active=False,
        vendor=vendor2
    )
    
    return {
        "vendors": [vendor1, vendor2],
        "consumer": consumer,
        "meals": [meal1, meal2, meal3, meal4]
    }


def test_calculate_distance():
    """Test the Haversine distance calculation function"""
    # Almaty to Astana, should be ~970 km
    distance = calculate_distance(43.238949, 76.889709, 51.128207, 71.430420)
    assert 950 < distance < 990
    
    # Close points within Almaty, should be ~12 km
    distance = calculate_distance(43.238949, 76.889709, 43.346065, 77.005005)
    assert 10 < distance < 15


@pytest.mark.asyncio
async def test_filter_meals_by_distance(setup_test_data):
    """Test filtering meals by distance"""
    meals = await Meal.filter(is_active=True).all()
    
    # From Almaty center, with 20km radius
    filtered_meals = await filter_meals_by_distance(meals, 43.238949, 76.889709, 20.0)
    assert len(filtered_meals) == 2
    
    # From Almaty center, with 5km radius (should only get meal1)
    filtered_meals = await filter_meals_by_distance(meals, 43.238949, 76.889709, 5.0)
    assert len(filtered_meals) == 1
    assert filtered_meals[0].name == "Test Meal 1"
    
    # From Astana (should only get meal3)
    filtered_meals = await filter_meals_by_distance(meals, 51.128207, 71.430420, 20.0)
    assert len(filtered_meals) == 1
    assert filtered_meals[0].name == "Far Away Meal"


@pytest.mark.asyncio
async def test_cmd_meals_nearby(setup_test_data):
    """Test the meals_nearby command"""
    # Mock message
    message = AsyncMock(spec=Message)
    message.from_user = AsyncMock(spec=User)
    message.from_user.id = 54321  # Consumer ID from setup
    
    # Mock state
    state = AsyncMock(spec=FSMContext)
    
    # Call the nearby meals command
    await cmd_meals_nearby(message, state)
    
    # Check that the correct keyboard and message is sent
    message.answer.assert_called_once()
    args, kwargs = message.answer.call_args
    
    assert args[0] == TEXT["meals_nearby_prompt"]
    assert "reply_markup" in kwargs


@pytest.mark.asyncio
async def test_process_meals_nearby(setup_test_data):
    """Test processing the location for nearby meals"""
    # Mock message with location
    message = AsyncMock(spec=Message)
    message.from_user = AsyncMock(spec=User)
    message.from_user.id = 54321  # Consumer ID from setup
    message.location = Location(latitude=43.238949, longitude=76.889709)  # Almaty center
    
    # Mock state
    state = AsyncMock(spec=FSMContext)
    
    # Call the nearby meals location processing
    await process_meals_nearby(message, state)
    
    # Check that state is cleared
    state.clear.assert_called_once()
    
    # Check that the correct message is sent
    message.answer.assert_called()
    
    # Get the first call arguments
    args = message.answer.call_args[0]
    message_text = args[0]
    
    # Check that the message contains the nearby meal (meal1)
    assert "Test Meal 1" in message_text
    assert "1500" in message_text
    
    # Check that the message contains the meal that's a bit further (meal2)
    assert "Test Meal 2" in message_text
    assert "2000.5" in message_text
    
    # Check that the far away meal is not included
    assert "Far Away Meal" not in message_text
    
    # Check that the inactive meal is not included
    assert "Inactive Meal" not in message_text


@pytest.mark.asyncio
async def test_view_meal(setup_test_data):
    """Test the view_meal command"""
    # Get meal ID from setup data
    meal = await Meal.filter(name="Test Meal 1").first()
    
    # Mock message
    message = AsyncMock(spec=Message)
    message.from_user = AsyncMock(spec=User)
    message.from_user.id = 54321  # Consumer ID from setup
    message.text = f"/view_meal {meal.id}"
    
    # Call the view meal command
    await cmd_view_meal(message)
    
    # Check that the correct message is sent
    message.answer.assert_called_once()
    
    # Get the first call arguments
    args, kwargs = message.answer.call_args
    message_text = args[0]
    
    # Check that the message contains all meal details
    assert "Test Meal 1" in message_text
    assert "Delicious test meal 1" in message_text
    assert "1500" in message_text
    assert "Test Vendor 1" in message_text
    assert "Test Address 1" in message_text
    
    # Check that the Buy button is included
    assert "reply_markup" in kwargs


@pytest.mark.asyncio
async def test_process_buy_callback(setup_test_data):
    """Test the buy meal callback handler"""
    # Get meal ID from setup data
    meal = await Meal.filter(name="Test Meal 1").first()
    
    # Mock callback query
    callback_query = AsyncMock(spec=CallbackQuery)
    callback_query.data = f"buy_meal:{meal.id}"
    callback_query.message = AsyncMock(spec=Message)
    
    # Call the buy meal callback handler
    await process_buy_callback(callback_query)
    
    # Check that the callback is answered
    callback_query.answer.assert_called_once()
    
    # Check that a message is sent to the user
    callback_query.message.answer.assert_called_once() 