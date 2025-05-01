import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from src.config import (
    WEBHOOK_PATH, WEBHOOK_URL, WEBAPP_HOST, WEBAPP_PORT,
    PAYMENT_WEBHOOK_SECRET
)
from src.main import handle_payment_webhook, on_startup, on_shutdown


# Set webhook mode for testing
os.environ["WEBHOOK_MODE"] = "True"
os.environ["TESTING"] = "True"


@pytest.fixture
def mock_bot():
    """Create a mock bot for testing webhook setup"""
    mock = AsyncMock()
    mock.set_webhook = AsyncMock()
    mock.delete_webhook = AsyncMock()
    return mock


@pytest.fixture
async def webhook_client():
    """Create a test client for the webhook handler"""
    app = web.Application()
    app.router.add_post('/payment-webhook', handle_payment_webhook)
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_on_startup_sets_webhook(mock_bot):
    """Test that on_startup sets the webhook URL"""
    await on_startup(mock_bot, WEBHOOK_URL)
    mock_bot.set_webhook.assert_called_once_with(WEBHOOK_URL)


@pytest.mark.asyncio
async def test_on_shutdown_removes_webhook(mock_bot):
    """Test that on_shutdown removes the webhook"""
    await on_shutdown(mock_bot)
    mock_bot.delete_webhook.assert_called_once()


@pytest.mark.asyncio
async def test_payment_webhook_processing(webhook_client):
    """Test that the payment webhook handler processes valid payments"""
    # Mock payment data
    payment_data = {
        "status": "completed",
        "order_id": 123,
        "payment_id": "payment_123",
        "amount": 1000,
        "currency": "KZT"
    }
    
    # Mock webhook signature
    headers = {
        "X-Signature": "test_signature"
    }
    
    # Mock process_payment_webhook function
    with patch("src.bot.process_payment_webhook", AsyncMock(return_value=True)):
        # Send request to webhook endpoint
        response = await webhook_client.post(
            '/payment-webhook',
            json=payment_data,
            headers=headers
        )
        
        # Check response
        assert response.status == 200
        response_data = await response.json()
        assert response_data["status"] == "success"


@pytest.mark.asyncio
async def test_payment_webhook_error_handling(webhook_client):
    """Test that the payment webhook handler handles errors properly"""
    # Mock invalid payment data
    payment_data = {
        "status": "invalid",
    }
    
    # Mock process_payment_webhook to raise an exception
    with patch("src.bot.process_payment_webhook", AsyncMock(side_effect=Exception("Test error"))):
        # Send request to webhook endpoint
        response = await webhook_client.post('/payment-webhook', json=payment_data)
        
        # Check response
        assert response.status == 400
        response_data = await response.json()
        assert response_data["status"] == "error"
        assert "message" in response_data


@pytest.mark.asyncio
async def test_payment_webhook_invalid_signature(webhook_client):
    """Test that the payment webhook handler rejects invalid signatures"""
    # Mock payment data
    payment_data = {
        "status": "completed",
        "order_id": 123,
    }
    
    # Mock process_payment_webhook to return False for invalid signatures
    with patch("src.bot.process_payment_webhook", AsyncMock(return_value=False)):
        # Send request to webhook endpoint
        response = await webhook_client.post('/payment-webhook', json=payment_data)
        
        # Check response
        assert response.status == 400
        response_data = await response.json()
        assert response_data["status"] == "error" 