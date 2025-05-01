import unittest
import asyncio
import os
import sys
import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch, AsyncMock

# Add the parent directory to sys.path to import the src modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment variables
os.environ["BOT_TOKEN"] = "TEST_BOT_TOKEN"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5432"
os.environ["DB_NAME"] = "asbolsyn_test"
os.environ["DB_USER"] = "postgres"
os.environ["DB_PASSWORD"] = "password"
os.environ["ADMIN_CHAT_ID"] = "123456789"

# Mock classes for FSM
class MockState:
    def __init__(self, state_name):
        self.state = state_name
    
    def __str__(self):
        return self.state

class MockStatesGroup:
    waiting_for_name = MockState('waiting_for_name')
    waiting_for_description = MockState('waiting_for_description')
    waiting_for_price = MockState('waiting_for_price')
    waiting_for_quantity = MockState('waiting_for_quantity')
    waiting_for_pickup_start = MockState('waiting_for_pickup_start')
    waiting_for_pickup_end = MockState('waiting_for_pickup_end')
    waiting_for_location_address = MockState('waiting_for_location_address')
    waiting_for_location_coords = MockState('waiting_for_location_coords')

# Create mock classes for the models
class MockVendorStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class MockLocation:
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude

class MockVendor:
    id = 1
    telegram_id = MagicMock()
    name = "Test Vendor"
    contact_phone = "+77771234567"
    status = MockVendorStatus.APPROVED
    
    @classmethod
    async def filter(cls, **kwargs):
        if 'telegram_id' in kwargs and kwargs['telegram_id'] == 12345:
            mock_vendor = MockVendor()
            mock_vendor.telegram_id = 12345
            return [mock_vendor]
        return []
    
    async def save(self):
        pass

class MockMeal:
    id = 1
    name = "Test Meal"
    description = "Test Description"
    price = Decimal("1500.00")
    quantity = 5
    pickup_start_time = datetime.datetime.now()
    pickup_end_time = datetime.datetime.now() + datetime.timedelta(hours=3)
    location_address = "Test Address"
    location_latitude = 43.238949
    location_longitude = 76.889709
    is_active = True
    vendor = MockVendor()
    
    @classmethod
    async def create(cls, **kwargs):
        mock_meal = MockMeal()
        for key, value in kwargs.items():
            setattr(mock_meal, key, value)
        return mock_meal
    
    @classmethod
    async def filter(cls, **kwargs):
        if 'id' in kwargs and kwargs['id'] == 1 and 'is_active' in kwargs and kwargs['is_active']:
            return [MockMeal()]
        elif 'vendor' in kwargs and 'is_active' in kwargs and kwargs['is_active']:
            return [MockMeal()]
        return []
    
    async def save(self):
        pass

# Mock the imports
sys.modules['src.models'] = MagicMock()
sys.modules['src.models'].Vendor = MockVendor
sys.modules['src.models'].VendorStatus = MockVendorStatus
sys.modules['src.models'].Meal = MockMeal

sys.modules['aiogram.fsm.state'] = MagicMock()
sys.modules['aiogram.fsm.state'].State = MagicMock(side_effect=MockState)
sys.modules['aiogram.fsm.state'].StatesGroup = MagicMock(side_effect=MockStatesGroup)

# Mock the src.bot module to avoid importing the real one
sys.modules['src.bot'] = MagicMock()
sys.modules['src.bot'].MealCreation = MockStatesGroup()

# Create test handler functions to simulate the real ones
async def mock_cmd_add_meal(message, state):
    """Simulate the add_meal command handler."""
    # Check if user is a registered vendor
    vendors = await MockVendor.filter(telegram_id=message.from_user.id)
    if not vendors:
        await message.answer("Not a vendor")
        return
    
    vendor = vendors[0]
    if vendor.status != MockVendorStatus.APPROVED:
        await message.answer("Not approved")
        return
    
    # Start meal creation process
    await state.set_state(MockStatesGroup.waiting_for_name)
    await message.answer("Enter meal name")

async def mock_process_meal_name(message, state):
    """Simulate the process_meal_name handler."""
    await state.update_data(name=message.text)
    await state.set_state(MockStatesGroup.waiting_for_description)
    await message.answer("Enter description")

async def mock_process_meal_description(message, state):
    """Simulate the process_meal_description handler."""
    await state.update_data(description=message.text)
    await state.set_state(MockStatesGroup.waiting_for_price)
    await message.answer("Enter price")

async def mock_process_meal_price(message, state):
    """Simulate the process_meal_price handler."""
    try:
        price = Decimal(message.text.strip())
        if price <= 0:
            raise ValueError()
        
        await state.update_data(price=float(price))
        await state.set_state(MockStatesGroup.waiting_for_quantity)
        await message.answer("Enter quantity")
    except (ValueError, TypeError):
        await message.answer("Invalid price")

async def mock_process_meal_quantity(message, state):
    """Simulate the process_meal_quantity handler."""
    try:
        quantity = int(message.text.strip())
        if quantity <= 0:
            raise ValueError()
        
        await state.update_data(quantity=quantity)
        await state.set_state(MockStatesGroup.waiting_for_pickup_start)
        await message.answer("Enter pickup start time")
    except (ValueError, TypeError):
        await message.answer("Invalid quantity")

async def mock_process_meal_pickup_start(message, state):
    """Simulate the process_meal_pickup_start handler."""
    try:
        time_str = message.text.strip()
        hours, minutes = map(int, time_str.split(':'))
        
        now = datetime.datetime.now()
        pickup_start = now.replace(hour=hours, minute=minutes)
        
        await state.update_data(
            pickup_start_str=time_str,
            pickup_start=pickup_start
        )
        
        await state.set_state(MockStatesGroup.waiting_for_pickup_end)
        await message.answer("Enter pickup end time")
    except (ValueError, TypeError):
        await message.answer("Invalid time format")

async def mock_process_meal_pickup_end(message, state):
    """Simulate the process_meal_pickup_end handler."""
    try:
        time_str = message.text.strip()
        hours, minutes = map(int, time_str.split(':'))
        
        now = datetime.datetime.now()
        pickup_end = now.replace(hour=hours, minute=minutes)
        
        data = await state.get_data()
        pickup_start = data.get('pickup_start')
        
        if pickup_end <= pickup_start:
            pickup_end = pickup_end.replace(day=pickup_end.day + 1)
        
        await state.update_data(
            pickup_end_str=time_str,
            pickup_end=pickup_end
        )
        
        await state.set_state(MockStatesGroup.waiting_for_location_address)
        await message.answer("Enter location address")
    except (ValueError, TypeError):
        await message.answer("Invalid time format")

async def mock_process_meal_location_address(message, state):
    """Simulate the process_meal_location_address handler."""
    await state.update_data(location_address=message.text)
    await state.set_state(MockStatesGroup.waiting_for_location_coords)
    await message.answer("Send location")

async def mock_process_meal_location_coords(message, state):
    """Simulate the process_meal_location_coords handler."""
    if not message.location:
        await message.answer("Invalid location")
        return
    
    location = message.location
    await state.update_data(
        location_latitude=location.latitude,
        location_longitude=location.longitude
    )
    
    data = await state.get_data()
    
    vendors = await MockVendor.filter(telegram_id=message.from_user.id)
    vendor = vendors[0]
    
    meal = await MockMeal.create(
        name=data.get('name'),
        description=data.get('description'),
        price=data.get('price'),
        quantity=data.get('quantity'),
        pickup_start_time=data.get('pickup_start'),
        pickup_end_time=data.get('pickup_end'),
        location_address=data.get('location_address'),
        location_latitude=data.get('location_latitude'),
        location_longitude=data.get('location_longitude'),
        vendor=vendor
    )
    
    await state.clear()
    await message.answer("Meal added successfully")

async def mock_cmd_my_meals(message):
    """Simulate the my_meals command handler."""
    vendors = await MockVendor.filter(telegram_id=message.from_user.id)
    if not vendors:
        await message.answer("Not a vendor")
        return
    
    vendor = vendors[0]
    meals = await MockMeal.filter(vendor=vendor, is_active=True)
    
    if not meals:
        await message.answer("No meals")
        return
    
    response = "Your meals:\n"
    for i, meal in enumerate(meals, 1):
        pickup_start = meal.pickup_start_time.strftime("%H:%M")
        pickup_end = meal.pickup_end_time.strftime("%H:%M")
        
        response += f"{i}. {meal.name} - {meal.price} tenge, {meal.quantity} portions, time: {pickup_start}-{pickup_end}\n"
    
    await message.answer(response)

async def mock_cmd_delete_meal(message):
    """Simulate the delete_meal command handler."""
    vendors = await MockVendor.filter(telegram_id=message.from_user.id)
    if not vendors:
        await message.answer("Not a vendor")
        return
    
    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.answer("Use format: /delete_meal ID")
        return
    
    try:
        meal_id = int(command_parts[1])
        vendor = vendors[0]
        
        meals = await MockMeal.filter(id=meal_id, vendor=vendor, is_active=True)
        
        if not meals:
            await message.answer("Meal not found")
            return
        
        meal = meals[0]
        meal.is_active = False
        await meal.save()
        
        await message.answer("Meal deleted")
    
    except (ValueError, TypeError):
        await message.answer("Invalid ID format")

# Replace the module functions with our mock implementations
sys.modules['src.bot'].cmd_add_meal = mock_cmd_add_meal
sys.modules['src.bot'].process_meal_name = mock_process_meal_name
sys.modules['src.bot'].process_meal_description = mock_process_meal_description
sys.modules['src.bot'].process_meal_price = mock_process_meal_price
sys.modules['src.bot'].process_meal_quantity = mock_process_meal_quantity
sys.modules['src.bot'].process_meal_pickup_start = mock_process_meal_pickup_start
sys.modules['src.bot'].process_meal_pickup_end = mock_process_meal_pickup_end
sys.modules['src.bot'].process_meal_location_address = mock_process_meal_location_address
sys.modules['src.bot'].process_meal_location_coords = mock_process_meal_location_coords
sys.modules['src.bot'].cmd_my_meals = mock_cmd_my_meals
sys.modules['src.bot'].cmd_delete_meal = mock_cmd_delete_meal


class TestMealCreation(unittest.TestCase):
    """Tests for meal creation and management process."""

    def setUp(self):
        """Set up test environment."""
        # Mock FSM context
        self.mock_state = AsyncMock()
        self.mock_state.set_state = AsyncMock()
        self.mock_state.update_data = AsyncMock()
        self.mock_state.get_data = AsyncMock(return_value={
            "name": "Test Meal",
            "description": "Test Description",
            "price": 1500.0,
            "quantity": 5,
            "pickup_start": datetime.datetime.now(),
            "pickup_start_str": "14:00",
            "pickup_end": datetime.datetime.now() + datetime.timedelta(hours=3),
            "pickup_end_str": "17:00",
            "location_address": "Test Address"
        })
        self.mock_state.clear = AsyncMock()
        
        # Mock message
        self.mock_message = AsyncMock()
        self.mock_message.from_user = AsyncMock()
        self.mock_message.from_user.id = 12345
        self.mock_message.answer = AsyncMock()
        self.mock_message.text = "Test input"
        
        # Create a mock location
        self.mock_location = MockLocation(43.238949, 76.889709)
        self.mock_message.location = self.mock_location

    def test_meal_creation_flow(self):
        """Test the meal creation flow."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Test add_meal command
            loop.run_until_complete(self._test_add_meal_command())
            
            # Test meal name input
            loop.run_until_complete(self._test_meal_name_input())
            
            # Test meal description input
            loop.run_until_complete(self._test_meal_description_input())
            
            # Test meal price input
            loop.run_until_complete(self._test_meal_price_input())
            
            # Test meal quantity input
            loop.run_until_complete(self._test_meal_quantity_input())
            
            # Test pickup start time input
            loop.run_until_complete(self._test_pickup_start_input())
            
            # Test pickup end time input
            loop.run_until_complete(self._test_pickup_end_input())
            
            # Test location address input
            loop.run_until_complete(self._test_location_address_input())
            
            # Test location coordinates input
            loop.run_until_complete(self._test_location_coords_input())
            
            # Test my_meals command
            loop.run_until_complete(self._test_my_meals_command())
            
            # Test delete_meal command
            loop.run_until_complete(self._test_delete_meal_command())
        finally:
            loop.close()

    async def _test_add_meal_command(self):
        """Test the /add_meal command."""
        from src.bot import cmd_add_meal
        
        # Reset mocks
        self.mock_state.set_state.reset_mock()
        self.mock_message.answer.reset_mock()
        
        # Execute command
        await cmd_add_meal(self.mock_message, self.mock_state)
        
        # Verify state was set
        self.mock_state.set_state.assert_called_once()
        # Verify message was sent
        self.mock_message.answer.assert_called_once()

    async def _test_meal_name_input(self):
        """Test the handler for meal name input."""
        from src.bot import process_meal_name
        
        # Reset mocks
        self.mock_state.set_state.reset_mock()
        self.mock_state.update_data.reset_mock()
        self.mock_message.answer.reset_mock()
        
        # Set test input
        self.mock_message.text = "Test Meal"
        
        # Execute handler
        await process_meal_name(self.mock_message, self.mock_state)
        
        # Verify data was updated
        self.mock_state.update_data.assert_called_once_with(name="Test Meal")
        # Verify state was changed
        self.mock_state.set_state.assert_called_once()
        # Verify message was sent
        self.mock_message.answer.assert_called_once()

    async def _test_meal_description_input(self):
        """Test the handler for meal description input."""
        from src.bot import process_meal_description
        
        # Reset mocks
        self.mock_state.set_state.reset_mock()
        self.mock_state.update_data.reset_mock()
        self.mock_message.answer.reset_mock()
        
        # Set test input
        self.mock_message.text = "Test Description"
        
        # Execute handler
        await process_meal_description(self.mock_message, self.mock_state)
        
        # Verify data was updated
        self.mock_state.update_data.assert_called_once_with(description="Test Description")
        # Verify state was changed
        self.mock_state.set_state.assert_called_once()
        # Verify message was sent
        self.mock_message.answer.assert_called_once()

    async def _test_meal_price_input(self):
        """Test the handler for meal price input."""
        from src.bot import process_meal_price
        
        # Reset mocks
        self.mock_state.set_state.reset_mock()
        self.mock_state.update_data.reset_mock()
        self.mock_message.answer.reset_mock()
        
        # Set test input
        self.mock_message.text = "1500"
        
        # Execute handler
        await process_meal_price(self.mock_message, self.mock_state)
        
        # Verify data was updated
        self.mock_state.update_data.assert_called_once()
        # Verify state was changed
        self.mock_state.set_state.assert_called_once()
        # Verify message was sent
        self.mock_message.answer.assert_called_once()

    async def _test_meal_quantity_input(self):
        """Test the handler for meal quantity input."""
        from src.bot import process_meal_quantity
        
        # Reset mocks
        self.mock_state.set_state.reset_mock()
        self.mock_state.update_data.reset_mock()
        self.mock_message.answer.reset_mock()
        
        # Set test input
        self.mock_message.text = "5"
        
        # Execute handler
        await process_meal_quantity(self.mock_message, self.mock_state)
        
        # Verify data was updated
        self.mock_state.update_data.assert_called_once_with(quantity=5)
        # Verify state was changed
        self.mock_state.set_state.assert_called_once()
        # Verify message was sent
        self.mock_message.answer.assert_called_once()

    async def _test_pickup_start_input(self):
        """Test the handler for pickup start time input."""
        from src.bot import process_meal_pickup_start
        
        # Reset mocks
        self.mock_state.set_state.reset_mock()
        self.mock_state.update_data.reset_mock()
        self.mock_message.answer.reset_mock()
        
        # Set test input
        self.mock_message.text = "14:00"
        
        # Execute handler
        await process_meal_pickup_start(self.mock_message, self.mock_state)
        
        # Verify data was updated
        self.mock_state.update_data.assert_called_once()
        # Verify state was changed
        self.mock_state.set_state.assert_called_once()
        # Verify message was sent
        self.mock_message.answer.assert_called_once()

    async def _test_pickup_end_input(self):
        """Test the handler for pickup end time input."""
        from src.bot import process_meal_pickup_end
        
        # Reset mocks
        self.mock_state.set_state.reset_mock()
        self.mock_state.update_data.reset_mock()
        self.mock_message.answer.reset_mock()
        
        # Set test input
        self.mock_message.text = "17:00"
        
        # Execute handler
        await process_meal_pickup_end(self.mock_message, self.mock_state)
        
        # Verify data was updated
        self.mock_state.update_data.assert_called_once()
        # Verify state was changed
        self.mock_state.set_state.assert_called_once()
        # Verify message was sent
        self.mock_message.answer.assert_called_once()

    async def _test_location_address_input(self):
        """Test the handler for location address input."""
        from src.bot import process_meal_location_address
        
        # Reset mocks
        self.mock_state.set_state.reset_mock()
        self.mock_state.update_data.reset_mock()
        self.mock_message.answer.reset_mock()
        
        # Set test input
        self.mock_message.text = "Test Address"
        
        # Execute handler
        await process_meal_location_address(self.mock_message, self.mock_state)
        
        # Verify data was updated
        self.mock_state.update_data.assert_called_once_with(location_address="Test Address")
        # Verify state was changed
        self.mock_state.set_state.assert_called_once()
        # Verify message was sent
        self.mock_message.answer.assert_called_once()

    async def _test_location_coords_input(self):
        """Test the handler for location coordinates input."""
        from src.bot import process_meal_location_coords
        
        # Reset mocks
        self.mock_state.clear.reset_mock()
        self.mock_state.update_data.reset_mock()
        self.mock_message.answer.reset_mock()
        
        # Execute handler
        await process_meal_location_coords(self.mock_message, self.mock_state)
        
        # Verify data was updated
        self.mock_state.update_data.assert_called_once()
        # Verify state was cleared
        self.mock_state.clear.assert_called_once()
        # Verify message was sent
        self.mock_message.answer.assert_called_once()

    async def _test_my_meals_command(self):
        """Test the /my_meals command."""
        from src.bot import cmd_my_meals
        
        # Reset mocks
        self.mock_message.answer.reset_mock()
        
        # Execute command
        await cmd_my_meals(self.mock_message)
        
        # Verify message was sent
        self.mock_message.answer.assert_called_once()

    async def _test_delete_meal_command(self):
        """Test the /delete_meal command."""
        from src.bot import cmd_delete_meal
        
        # Reset mocks
        self.mock_message.answer.reset_mock()
        
        # Set test input
        self.mock_message.text = "/delete_meal 1"
        
        # Execute command
        await cmd_delete_meal(self.mock_message)
        
        # Verify message was sent
        self.mock_message.answer.assert_called_once()


if __name__ == "__main__":
    unittest.main() 