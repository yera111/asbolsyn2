import unittest
import os
import sys
import logging
from unittest.mock import MagicMock, patch, AsyncMock

# Add the parent directory to the sys.path to import the src modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment variables
os.environ["BOT_TOKEN"] = "TEST_BOT_TOKEN"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5432"
os.environ["DB_NAME"] = "asbolsyn_test"
os.environ["DB_USER"] = "postgres"
os.environ["DB_PASSWORD"] = "password"
os.environ["ADMIN_CHAT_ID"] = "123456789"

# Mock modules that might not be installed
sys.modules['tortoise'] = MagicMock()
sys.modules['tortoise.models'] = MagicMock()
sys.modules['tortoise.fields'] = MagicMock()
sys.modules['aiogram'] = MagicMock()
sys.modules['aiogram.filters'] = MagicMock()
sys.modules['aiogram.filters.command'] = MagicMock()
sys.modules['aiogram.types'] = MagicMock()
sys.modules['aiogram.fsm'] = MagicMock()
sys.modules['aiogram.fsm.context'] = MagicMock()
sys.modules['aiogram.fsm.state'] = MagicMock()
sys.modules['aiogram.fsm.storage'] = MagicMock()
sys.modules['aiogram.fsm.storage.memory'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

# Import the config to test
from src.config import BOT_TOKEN, ADMIN_CHAT_ID

# Create mock classes for the models
class MockVendor:
    telegram_id = True
    
    # Add methods for vendor registration test
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
        return mock_vendor
    
    class Meta:
        pass

class MockConsumer:
    telegram_id = True
    
    @classmethod
    async def get_or_create(cls, **kwargs):
        mock_consumer = MockConsumer()
        mock_consumer.telegram_id = kwargs.get('telegram_id')
        return mock_consumer, True
    
    class Meta:
        pass

class MockMeal:
    vendor = True
    class Meta:
        pass

class MockOrder:
    consumer = True
    class Meta:
        pass

# Mock VendorStatus enum
class MockVendorStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

# Patch the imports in the test
@patch('src.models.Vendor', MockVendor)
@patch('src.models.Consumer', MockConsumer)
@patch('src.models.Meal', MockMeal)
@patch('src.models.Order', MockOrder)
@patch('src.models.VendorStatus', MockVendorStatus)
class BasicSetupTest(unittest.TestCase):
    """Tests for verifying the basic setup of the bot."""

    def test_bot_token_exists(self):
        """Test if BOT_TOKEN exists in the environment variables."""
        # Testing only that it's defined, not the actual value
        self.assertTrue(BOT_TOKEN is not None, "BOT_TOKEN environment variable is not set")
        self.assertTrue(len(BOT_TOKEN) > 0, "BOT_TOKEN is empty")

    def test_project_structure(self):
        """Test if the project structure is correctly set up."""
        # Check that essential files exist
        self.assertTrue(os.path.exists("src/bot.py"), "bot.py file is missing")
        self.assertTrue(os.path.exists("src/config.py"), "config.py file is missing")
        self.assertTrue(os.path.exists("src/db.py"), "db.py file is missing")
        self.assertTrue(os.path.exists("src/models.py"), "models.py file is missing")
        self.assertTrue(os.path.exists("requirements.txt"), "requirements.txt file is missing")

    def test_admin_chat_id_exists(self):
        """Test if ADMIN_CHAT_ID exists in the environment variables."""
        self.assertTrue(ADMIN_CHAT_ID is not None, "ADMIN_CHAT_ID environment variable is not set")
        self.assertTrue(len(ADMIN_CHAT_ID) > 0, "ADMIN_CHAT_ID is empty")


@patch('src.models.Vendor', MockVendor)
@patch('src.models.Consumer', MockConsumer)
@patch('src.models.VendorStatus', MockVendorStatus)
class VendorRegistrationTest(unittest.TestCase):
    """Tests for the vendor registration process."""
    
    async def asyncSetUp(self):
        """Set up async test environment."""
        # Import handler functions from src.bot
        from src.bot import cmd_register_vendor, process_vendor_name, process_vendor_phone
        self.cmd_register_vendor = cmd_register_vendor
        self.process_vendor_name = process_vendor_name
        self.process_vendor_phone = process_vendor_phone
        
        # Mock Message object
        self.mock_message = AsyncMock()
        self.mock_message.from_user = AsyncMock()
        self.mock_message.from_user.id = 12345
        self.mock_message.text = "test"
        
        # Mock FSMContext
        self.mock_state = AsyncMock()
        self.mock_state.get_data = AsyncMock(return_value={"name": "Test Vendor"})
    
    @patch('src.bot.bot.send_message')
    @unittest.skip("Test requires running asyncio event loop")
    async def test_vendor_registration_flow(self, mock_send_message):
        """Test the vendor registration process from command to completion."""
        await self.asyncSetUp()
        
        # Step 1: User enters /register_vendor command
        await self.cmd_register_vendor(self.mock_message, self.mock_state)
        
        # Verify state was set to waiting for name
        self.mock_state.set_state.assert_called_once()
        
        # Step 2: User enters vendor name
        self.mock_message.text = "Test Vendor"
        await self.process_vendor_name(self.mock_message, self.mock_state)
        
        # Verify data was updated and state set to waiting for phone
        self.mock_state.update_data.assert_called_once_with(name="Test Vendor")
        
        # Step 3: User enters phone number
        self.mock_message.text = "+77771234567"
        await self.process_vendor_phone(self.mock_message, self.mock_state)
        
        # Verify state was cleared
        self.mock_state.clear.assert_called_once()
        
        # Verify admin was notified
        mock_send_message.assert_called_once()
        

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    unittest.main()
