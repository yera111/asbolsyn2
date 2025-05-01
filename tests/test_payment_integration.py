import pytest
import re
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from aiogram.types import User, Chat, Message, CallbackQuery
import pytest_asyncio

from src.models import Vendor, Consumer, Meal, Order, OrderStatus, VendorStatus
from src.bot import process_buy_callback


@pytest.fixture
def mock_bot():
    """Create a mock bot instance"""
    return AsyncMock()


@pytest.fixture
def mock_payment_gateway():
    """Create a mock payment gateway"""
    with patch("src.payment.payment_gateway") as mock_gateway:
        # Configure the create_payment method
        mock_gateway.create_payment.return_value = ("test_payment_id", "https://test-payment.kz/pay")
        yield mock_gateway


@pytest_asyncio.fixture
async def test_data():
    """Create test data for integration tests"""
    consumer = await Consumer.create(telegram_id=12345)
    vendor = await Vendor.create(
        telegram_id=54321,
        name="Test Integration Vendor",
        status=VendorStatus.APPROVED
    )
    meal = await Meal.create(
        vendor=vendor,
        name="Test Integration Meal",
        description="A test meal for integration",
        price=Decimal("200.00"),
        quantity=10,
        pickup_start_time="2025-06-01T18:00:00",
        pickup_end_time="2025-06-01T20:00:00",
        location_address="Integration Test Address",
        location_latitude=43.238949,
        location_longitude=76.889709,
        is_active=True
    )
    
    return {"consumer": consumer, "vendor": vendor, "meal": meal}


@pytest.mark.asyncio
async def test_process_buy_callback(mock_bot, mock_payment_gateway, test_data):
    """Test the buy meal callback handler"""
    with patch("src.bot.bot", mock_bot):
        # Create mock callback query
        callback_query = AsyncMock(spec=CallbackQuery)
        callback_query.from_user = User(id=test_data["consumer"].telegram_id, is_bot=False, first_name="Test")
        callback_query.message = AsyncMock(spec=Message)
        callback_query.message.chat = Chat(id=test_data["consumer"].telegram_id, type="private")
        callback_query.data = f"buy_meal:{test_data['meal'].id}:3"  # Buy 3 portions
        
        # Call the handler
        await process_buy_callback(callback_query)
        
        # Check mock_payment_gateway was called
        mock_payment_gateway.create_payment.assert_called_once()
        
        # Verify order was created in database
        order = await Order.filter(consumer_id=test_data["consumer"].id, meal_id=test_data["meal"].id).first()
        assert order is not None
        assert order.status == OrderStatus.PENDING
        assert order.payment_id == "test_payment_id"
        assert order.quantity == 3
        
        # Verify correct messages were sent
        mock_bot.send_message.assert_not_called()  # Messages are sent to the message object, not directly via bot
        
        # Verify the answer callback was called
        callback_query.answer.assert_called_once()
        
        # Verify the message respond was called with payment URL
        assert callback_query.message.answer.call_count >= 1
        
        # Check first call contains order info and payment link
        first_call_args = callback_query.message.answer.call_args_list[0][0]
        first_call_text = first_call_args[0]
        first_call_markup = first_call_args[1]['reply_markup']
        
        assert f"Заказ #{order.id} создан" in first_call_text
        assert "3 порций" in first_call_text
        assert "200.00" in first_call_text or "600.00" in first_call_text  # Either unit price or total
        assert "Test Integration Meal" in first_call_text
        
        # Verify payment URL was included
        assert any("Перейти к оплате" in button.text for row in first_call_markup.inline_keyboard for button in row)
        assert any("https://test-payment.kz/pay" in button.url for row in first_call_markup.inline_keyboard for button in row)


@pytest.mark.asyncio
async def test_out_of_stock_handling(mock_bot, test_data):
    """Test handling when meal has insufficient quantity"""
    with patch("src.bot.bot", mock_bot):
        # Update meal to have only 1 portion left
        meal = test_data["meal"]
        meal.quantity = 1
        await meal.save()
        
        # Create mock callback query requesting 3 portions
        callback_query = AsyncMock(spec=CallbackQuery)
        callback_query.from_user = User(id=test_data["consumer"].telegram_id, is_bot=False, first_name="Test")
        callback_query.message = AsyncMock(spec=Message)
        callback_query.message.chat = Chat(id=test_data["consumer"].telegram_id, type="private")
        callback_query.data = f"buy_meal:{meal.id}:3"  # Try to buy 3 portions when only 1 is available
        
        # Call the handler
        await process_buy_callback(callback_query)
        
        # Verify the answer callback was called with error message
        callback_query.answer.assert_called_once()
        assert "Недостаточно порций" in callback_query.answer.call_args[0][0]
        
        # Verify no order was created
        order_count = await Order.filter(consumer_id=test_data["consumer"].id, meal_id=meal.id).count()
        assert order_count == 0


@pytest.mark.asyncio
async def test_payment_gateway_error_handling(mock_bot, test_data):
    """Test handling when payment gateway fails"""
    # Mock payment gateway to return failure
    with patch("src.payment.payment_gateway.create_payment", return_value=(None, None)), \
         patch("src.bot.bot", mock_bot):
        
        # Create mock callback query
        callback_query = AsyncMock(spec=CallbackQuery)
        callback_query.from_user = User(id=test_data["consumer"].telegram_id, is_bot=False, first_name="Test")
        callback_query.message = AsyncMock(spec=Message)
        callback_query.message.chat = Chat(id=test_data["consumer"].telegram_id, type="private")
        callback_query.data = f"buy_meal:{test_data['meal'].id}:2"  # Buy 2 portions
        
        # Call the handler
        await process_buy_callback(callback_query)
        
        # Verify the answer callback was called with error message
        callback_query.answer.assert_called_once()
        assert "Не удалось создать платеж" in callback_query.answer.call_args[0][0] 