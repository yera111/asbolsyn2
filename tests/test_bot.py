import unittest
import os
import sys
import logging
from unittest.mock import MagicMock, patch

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
sys.modules['dotenv'] = MagicMock()

# Import the config to test
from src.config import BOT_TOKEN

# Create mock classes for the models
class MockVendor:
    telegram_id = True
    class Meta:
        pass

class MockConsumer:
    telegram_id = True
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

# Patch the imports in the test
@patch('src.models.Vendor', MockVendor)
@patch('src.models.Consumer', MockConsumer)
@patch('src.models.Meal', MockMeal)
@patch('src.models.Order', MockOrder)
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


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    unittest.main()
