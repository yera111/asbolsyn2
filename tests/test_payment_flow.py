import pytest
import unittest.mock as mock
from decimal import Decimal
import os
import pytest_asyncio
from unittest.mock import patch

from src.models import Vendor, Consumer, Meal, Order, OrderStatus, VendorStatus
from src.payment import PaymentGateway

# Set up environment variables for testing
TEST_ENV = {
    "PAYMENT_GATEWAY_API_KEY": "test_api_key",
    "PAYMENT_GATEWAY_SECRET": "test_secret",
    "PAYMENT_GATEWAY_URL": "https://test-payment.kz",
    "PAYMENT_GATEWAY_ENABLED": "True",
    "PAYMENT_WEBHOOK_SECRET": "webhook_secret"
}

@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables for payment gateway tests"""
    original_values = {}
    for key, value in TEST_ENV.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original environment variables
    for key, value in original_values.items():
        if value is None:
            if key in os.environ:
                del os.environ[key]
        else:
            os.environ[key] = value


@pytest.mark.asyncio
async def test_payment_gateway_init():
    """Test payment gateway initialization"""
    gateway = PaymentGateway()
    assert gateway.enabled is not None
    assert gateway.api_key is not None
    assert gateway.base_url is not None
    assert gateway.secret is not None


@pytest.mark.asyncio
async def test_create_payment():
    """Test creating a payment for an order"""
    gateway = PaymentGateway()
    
    order_id = 123
    amount = Decimal("100.00")
    description = "Test payment"
    
    payment_id, payment_url = await gateway.create_payment(order_id, amount, description)
    
    assert payment_id is not None
    assert payment_url is not None
    assert str(order_id) in payment_url
    assert gateway.base_url in payment_url


@pytest.mark.asyncio
async def test_verify_webhook_signature():
    """Test webhook signature verification"""
    gateway = PaymentGateway()
    
    # In test mode, verification should always pass
    payload = '{"payment_id": "test123", "status": "completed"}'
    signature = "invalid_signature"
    
    result = gateway.verify_webhook_signature(payload, signature)
    assert result is True


@pytest_asyncio.fixture
async def test_order_data():
    """Create test data for webhook processing tests"""
    # Create required models
    consumer = await Consumer.create(telegram_id=123456789)
    vendor = await Vendor.create(
        telegram_id=987654321,
        name="Test Vendor",
        status=VendorStatus.APPROVED
    )
    meal = await Meal.create(
        vendor=vendor,
        name="Test Meal",
        description="A test meal",
        price=Decimal("100.00"),
        quantity=5,
        pickup_start_time="2025-06-01T12:00:00",
        pickup_end_time="2025-06-01T14:00:00",
        location_address="Test Address",
        location_latitude=43.238949,
        location_longitude=76.889709,
        is_active=True
    )
    order = await Order.create(
        consumer=consumer,
        meal=meal,
        status=OrderStatus.PENDING,
        payment_id="orig_payment_id",
        quantity=2
    )
    
    return {
        "consumer": consumer,
        "vendor": vendor,
        "meal": meal,
        "order": order
    }


@pytest.mark.asyncio
async def test_process_webhook(test_order_data):
    """Test processing a webhook notification"""
    order = test_order_data["order"]
    
    # Create webhook data
    webhook_data = {
        "payment_id": "test_payment_id",
        "status": "completed",
        "order_id": order.id,
        "timestamp": "2025-06-01T13:00:00"
    }
    
    # Disable actual notifications
    with patch("src.payment.payment_gateway.send_order_notifications", return_value=None):
        # Process webhook
        gateway = PaymentGateway()
        result = await gateway.process_webhook(webhook_data)
        
        # Verify result
        assert result is True
        
        # Refresh order from database
        updated_order = await Order.get(id=order.id)
        assert updated_order.status == OrderStatus.PAID
        assert updated_order.payment_id == "test_payment_id"
        
        # Refresh meal from database
        meal = test_order_data["meal"]
        updated_meal = await Meal.get(id=meal.id)
        assert updated_meal.quantity == 3  # 5 initial - 2 ordered


@pytest.mark.asyncio
async def test_process_webhook_invalid_order():
    """Test processing a webhook with an invalid order ID"""
    gateway = PaymentGateway()
    
    # Invalid order ID
    webhook_data = {
        "payment_id": "test_payment_id",
        "status": "completed",
        "order_id": 9999,  # Non-existent order
        "timestamp": "2025-06-01T13:00:00"
    }
    
    # Process webhook should handle errors gracefully
    result = await gateway.process_webhook(webhook_data)
    assert result is False


@pytest_asyncio.fixture
async def test_order_data_non_completed():
    """Create test data for non-completed webhook tests"""
    consumer = await Consumer.create(telegram_id=123456790)
    vendor = await Vendor.create(
        telegram_id=987654320,
        name="Test Vendor 2",
        status=VendorStatus.APPROVED
    )
    meal = await Meal.create(
        vendor=vendor,
        name="Test Meal 2",
        description="Another test meal",
        price=Decimal("150.00"),
        quantity=3,
        pickup_start_time="2025-06-01T12:00:00",
        pickup_end_time="2025-06-01T14:00:00",
        location_address="Test Address 2",
        location_latitude=43.238949,
        location_longitude=76.889709,
        is_active=True
    )
    order = await Order.create(
        consumer=consumer,
        meal=meal,
        status=OrderStatus.PENDING,
        payment_id="orig_payment_id_2",
        quantity=1
    )
    
    return {
        "consumer": consumer,
        "vendor": vendor,
        "meal": meal,
        "order": order
    }


@pytest.mark.asyncio
async def test_process_webhook_non_completed_status(test_order_data_non_completed):
    """Test processing a webhook with a non-completed status"""
    order = test_order_data_non_completed["order"]
    meal = test_order_data_non_completed["meal"]
    
    # Create webhook data with non-completed status
    webhook_data = {
        "payment_id": "test_payment_id_2",
        "status": "failed",  # Non-completed status
        "order_id": order.id,
        "timestamp": "2025-06-01T13:00:00"
    }
    
    # Process webhook
    gateway = PaymentGateway()
    result = await gateway.process_webhook(webhook_data)
    
    # Verify result (should be true since processing succeeded, even though order wasn't updated)
    assert result is True
    
    # Refresh order from database
    updated_order = await Order.get(id=order.id)
    assert updated_order.status == OrderStatus.PENDING
    assert updated_order.payment_id == "orig_payment_id_2"
    
    # Refresh meal from database
    updated_meal = await Meal.get(id=meal.id)
    assert updated_meal.quantity == 3  # Still 3 