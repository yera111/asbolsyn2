import logging
import asyncio
import uuid
import hmac
import hashlib
from .config import (
    PAYMENT_GATEWAY_ENABLED,
    PAYMENT_GATEWAY_API_KEY,
    PAYMENT_GATEWAY_SECRET,
    PAYMENT_GATEWAY_URL,
    PAYMENT_WEBHOOK_SECRET,
    PAYMENT_SUCCESS_URL,
    PAYMENT_FAILURE_URL,
    TELEGRAM_PAYMENT_ENABLED,
    TELEGRAM_PAYMENT_PROVIDER_TOKEN,
    TELEGRAM_PAYMENT_CURRENCY
)
from .models import Order, OrderStatus, Meal

logger = logging.getLogger(__name__)

class PaymentGateway:
    """
    Payment gateway integration for As Bolsyn.
    Supports both:
    1. Telegram's built-in payment system (preferred when enabled)
    2. External payment provider (legacy/fallback method)
    """
    
    def __init__(self):
        """Initialize the payment gateway service."""
        self.enabled = PAYMENT_GATEWAY_ENABLED
        self.api_key = PAYMENT_GATEWAY_API_KEY
        self.secret = PAYMENT_GATEWAY_SECRET
        self.base_url = PAYMENT_GATEWAY_URL
        
        # Telegram payment settings
        self.telegram_payment_enabled = TELEGRAM_PAYMENT_ENABLED
        self.telegram_provider_token = TELEGRAM_PAYMENT_PROVIDER_TOKEN
        self.currency = TELEGRAM_PAYMENT_CURRENCY
    
    def is_telegram_payments_available(self):
        """Check if Telegram payments are available and configured."""
        return (self.telegram_payment_enabled and 
                self.telegram_provider_token and 
                len(self.telegram_provider_token) > 5)
    
    async def create_payment(self, order_id, amount, description=None):
        """
        Create a payment for an order.
        
        If Telegram payments are available, this will simply return a flag indicating 
        that the Telegram payment flow should be used.
        
        If Telegram payments are not available, it will fall back to the legacy external payment flow.
        
        Args:
            order_id: The unique order identifier
            amount: The payment amount
            description: Optional payment description
            
        Returns:
            tuple: (payment_id, payment_url) for external payments, or
                  (payment_id, None) for Telegram payments
        """
        # If Telegram payments are enabled and configured, use the built-in payment system
        if self.is_telegram_payments_available():
            # For Telegram payments, we only need to return a payment ID
            # The actual payment will be initiated via the Telegram API with an invoice
            payment_id = f"TG-{order_id}-{int(uuid.uuid4())}"
            logger.info(f"Creating Telegram payment {payment_id} for order {order_id} with amount {amount}")
            return payment_id, None
            
        # Otherwise, fall back to the legacy external payment gateway flow
        if not self.enabled:
            logger.warning("Payment gateway is disabled.")
            return None, None
            
        # Generate a unique payment ID
        payment_id = f"EXT-{order_id}-{int(uuid.uuid4())}"
        
        # In a real implementation, this would make an API call to the payment gateway
        # For the MVP, we'll simulate the payment flow
        logger.info(f"Creating external payment {payment_id} for order {order_id} with amount {amount}")
        
        # Ensure we have valid URLs even when environment variables aren't set
        base_url = self.base_url or "https://example.com"
        success_url = PAYMENT_SUCCESS_URL or "https://t.me/as_bolsyn_bot"
        failure_url = PAYMENT_FAILURE_URL or "https://t.me/as_bolsyn_bot"
        
        # Generate a simulated payment URL
        success_redirect = f"{success_url}?order_id={order_id}&payment_id={payment_id}"
        failure_redirect = f"{failure_url}?order_id={order_id}&payment_id={payment_id}"
        
        # Create a simulated payment URL with proper HTTP format
        payment_url = f"{base_url}/pay?order_id={order_id}&amount={amount}&payment_id={payment_id}&success_url={success_redirect}&failure_url={failure_redirect}"
        
        # In a real implementation, the payment URL would be returned by the payment gateway
        return payment_id, payment_url
    
    def verify_webhook_signature(self, payload, signature):
        """
        Verify that the webhook payload signature matches the expected value.
        
        Args:
            payload: The webhook payload as a string
            signature: The signature to verify
            
        Returns:
            bool: True if the signature is valid, False otherwise
        """
        if not self.enabled or not PAYMENT_WEBHOOK_SECRET:
            # In testing mode, always return true
            return True
            
        expected_signature = hmac.new(
            PAYMENT_WEBHOOK_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    async def process_webhook(self, data):
        """
        Process a webhook notification from the payment gateway.
        
        Args:
            data: The webhook payload
            
        Returns:
            bool: True if processing succeeded, False otherwise
        """
        try:
            payment_id = data.get("payment_id")
            status = data.get("status")
            order_id = data.get("order_id")
            
            if not payment_id or not status or not order_id:
                logger.error("Missing required webhook fields")
                return False
                
            if status != "completed":
                logger.info(f"Payment {payment_id} status is {status}, not updating order")
                return True
                
            # Get the order from the database
            try:
                order = await Order.get(id=order_id)
            except Exception as e:
                logger.error(f"Error retrieving order {order_id}: {e}")
                return False
                
            # Update order status
            order.status = OrderStatus.PAID
            order.payment_id = payment_id
            await order.save()
            
            # Update meal quantity
            meal = await order.meal
            meal.quantity -= order.quantity
            if meal.quantity < 0:
                meal.quantity = 0
            await meal.save()
            
            logger.info(f"Order {order_id} marked as paid with payment {payment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return False

# Create a singleton instance
payment_gateway = PaymentGateway() 