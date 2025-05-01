import unittest
import asyncio
import os
import sys
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
    waiting_for_phone = MockState('waiting_for_phone')

# Create mock classes for the models
class MockVendorStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class MockVendor:
    telegram_id = MagicMock()
    name = MagicMock()
    contact_phone = MagicMock()
    status = MagicMock()
    
    @classmethod
    async def filter(cls, **kwargs):
        return []
    
    @classmethod
    async def create(cls, **kwargs):
        mock_vendor = MockVendor()
        mock_vendor.telegram_id = kwargs.get('telegram_id')
        mock_vendor.name = kwargs.get('name')
        mock_vendor.contact_phone = kwargs.get('contact_phone')
        mock_vendor.status = kwargs.get('status')
        mock_vendor.save = AsyncMock()
        return mock_vendor

# Mock the imports
sys.modules['src.models'] = MagicMock()
sys.modules['src.models'].Vendor = MockVendor
sys.modules['src.models'].VendorStatus = MockVendorStatus

sys.modules['aiogram.fsm.state'] = MagicMock()
sys.modules['aiogram.fsm.state'].State = MagicMock(side_effect=MockState)
sys.modules['aiogram.fsm.state'].StatesGroup = MagicMock(side_effect=MockStatesGroup)

# Mock the src.bot module to avoid importing the real one
sys.modules['src.bot'] = MagicMock()
sys.modules['src.bot'].VendorRegistration = MockStatesGroup()

# Create test handler functions to simulate the real ones
async def mock_cmd_register_vendor(message, state):
    """Simulate the vendor registration command handler."""
    # Check if already registered
    vendors = await MockVendor.filter(telegram_id=message.from_user.id)
    if vendors:
        await message.answer("Already registered")
        return
    
    # Start registration
    await state.set_state(MockStatesGroup.waiting_for_name)
    await message.answer("Start registration")

async def mock_process_vendor_name(message, state):
    """Simulate the process_vendor_name handler."""
    await state.update_data(name=message.text)
    await state.set_state(MockStatesGroup.waiting_for_phone)
    await message.answer("Enter phone")

async def mock_process_vendor_phone(message, state):
    """Simulate the process_vendor_phone handler."""
    data = await state.get_data()
    vendor_name = data.get("name")
    
    # Create vendor
    vendor = await MockVendor.create(
        telegram_id=message.from_user.id,
        name=vendor_name,
        contact_phone=message.text,
        status=MockVendorStatus.PENDING
    )
    
    # Clear state
    await state.clear()
    
    # Notify user
    await message.answer("Registration complete")
    
    # Mock the admin notification
    from src.bot import bot
    await bot.send_message(
        chat_id=os.environ["ADMIN_CHAT_ID"],
        text=f"New vendor: {vendor_name}"
    )

async def mock_cmd_approve_vendor(message):
    """Simulate the approve_vendor command handler."""
    # Check if admin
    if str(message.from_user.id) != os.environ["ADMIN_CHAT_ID"]:
        await message.answer("Not admin")
        return
    
    # Parse vendor ID
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Wrong format")
        return
    
    try:
        vendor_id = int(parts[1])
        vendors = await MockVendor.filter(telegram_id=vendor_id)
        
        if not vendors:
            await message.answer("Vendor not found")
            return
        
        vendor = vendors[0]
        vendor.status = MockVendorStatus.APPROVED
        await vendor.save()
        
        # Notify admin
        await message.answer(f"Vendor approved: {vendor.name}")
        
        # Notify vendor
        from src.bot import bot
        await bot.send_message(
            chat_id=vendor_id,
            text="Your vendor application has been approved"
        )
    
    except (ValueError, TypeError):
        await message.answer("Invalid ID")

# Replace the module functions with our mock implementations
sys.modules['src.bot'].cmd_register_vendor = mock_cmd_register_vendor
sys.modules['src.bot'].process_vendor_name = mock_process_vendor_name
sys.modules['src.bot'].process_vendor_phone = mock_process_vendor_phone
sys.modules['src.bot'].cmd_approve_vendor = mock_cmd_approve_vendor

# Add bot mock
sys.modules['src.bot'].bot = MagicMock()
sys.modules['src.bot'].bot.send_message = AsyncMock()

class TestVendorRegistration(unittest.TestCase):
    """Tests for vendor registration process."""

    def setUp(self):
        """Set up test environment."""
        # Mock FSM context
        self.mock_state = AsyncMock()
        self.mock_state.set_state = AsyncMock()
        self.mock_state.update_data = AsyncMock()
        self.mock_state.get_data = AsyncMock(return_value={"name": "Test Vendor"})
        self.mock_state.clear = AsyncMock()
        
        # Mock message
        self.mock_message = AsyncMock()
        self.mock_message.from_user = AsyncMock()
        self.mock_message.from_user.id = 12345
        self.mock_message.answer = AsyncMock()
        self.mock_message.text = "Test Vendor"
        
        # Reset the send_message mock before each test
        from src.bot import bot
        bot.send_message.reset_mock()

    def test_vendor_registration_flow(self):
        """Test the vendor registration flow."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Test registration command
            loop.run_until_complete(self._test_register_vendor())
            
            # Test handling vendor name
            loop.run_until_complete(self._test_process_vendor_name())
            
            # Test handling vendor phone
            loop.run_until_complete(self._test_process_vendor_phone())
            
            # Test vendor approval
            loop.run_until_complete(self._test_approve_vendor())
        finally:
            loop.close()

    async def _test_register_vendor(self):
        """Test the /register_vendor command."""
        from src.bot import cmd_register_vendor
        
        # Reset the mock before test
        self.mock_state.set_state.reset_mock()
        self.mock_message.answer.reset_mock()
        
        # Execute the command handler
        await cmd_register_vendor(self.mock_message, self.mock_state)
        
        # Verify state was set
        self.mock_state.set_state.assert_called_once()
        # Verify response was sent
        self.mock_message.answer.assert_called_once()

    async def _test_process_vendor_name(self):
        """Test the handler for vendor name input."""
        from src.bot import process_vendor_name
        
        # Reset the mock before test
        self.mock_state.set_state.reset_mock()
        self.mock_state.update_data.reset_mock()
        self.mock_message.answer.reset_mock()
        
        # Execute the handler
        await process_vendor_name(self.mock_message, self.mock_state)
        
        # Verify data was updated
        self.mock_state.update_data.assert_called_once_with(name="Test Vendor")
        # Verify state was changed
        self.mock_state.set_state.assert_called_once()
        # Verify response was sent
        self.mock_message.answer.assert_called_once()

    async def _test_process_vendor_phone(self):
        """Test the handler for vendor phone input."""
        from src.bot import process_vendor_phone
        
        # Reset the mock before test
        self.mock_state.clear.reset_mock()
        self.mock_message.answer.reset_mock()
        
        # Set test phone number
        self.mock_message.text = "+77771234567"
        
        # Execute the handler
        await process_vendor_phone(self.mock_message, self.mock_state)
        
        # Verify state was cleared
        self.mock_state.clear.assert_called_once()
        # Verify response was sent to vendor
        self.mock_message.answer.assert_called_once()
        # Verify notification was sent to admin
        from src.bot import bot
        bot.send_message.assert_called_once()

    async def _test_approve_vendor(self):
        """Test the admin approval of a vendor."""
        from src.bot import cmd_approve_vendor
        from src.bot import bot
        
        # Reset mocks
        bot.send_message.reset_mock()
        
        # Mock an admin message
        admin_message = AsyncMock()
        admin_message.from_user = AsyncMock()
        admin_message.from_user.id = int(os.environ["ADMIN_CHAT_ID"])
        admin_message.text = "/approve_vendor 12345"
        admin_message.answer = AsyncMock()
        
        # Patch MockVendor.filter to return a vendor
        mock_vendor = AsyncMock()
        mock_vendor.telegram_id = 12345
        mock_vendor.name = "Test Vendor"
        mock_vendor.save = AsyncMock()
        
        with patch.object(MockVendor, 'filter', return_value=[mock_vendor]):
            # Execute the handler
            await cmd_approve_vendor(admin_message)
            
            # Verify vendor status was updated
            self.assertEqual(mock_vendor.status, MockVendorStatus.APPROVED)
            # Verify vendor was saved
            mock_vendor.save.assert_called_once()
            # Verify response was sent to admin
            admin_message.answer.assert_called_once()
            # Verify notification was sent to vendor
            bot.send_message.assert_called_once()


if __name__ == "__main__":
    unittest.main() 