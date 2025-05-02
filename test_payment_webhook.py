#!/usr/bin/env python
"""
Test script for As Bolsyn payment webhooks.
This script sends a test payment webhook to verify the webhook integration.
"""

import argparse
import json
import requests
import logging
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_test_webhook(webhook_url, order_id, payment_id="test_payment_123", status="completed"):
    """
    Send a test payment webhook to the specified URL.
    
    Args:
        webhook_url: The URL to send the webhook to
        order_id: The ID of the order to update
        payment_id: The payment ID (default: test_payment_123)
        status: The payment status (default: completed)
        
    Returns:
        bool: True if the webhook was successfully processed, False otherwise
    """
    # Prepare webhook payload
    payload = {
        "payment_id": payment_id,
        "status": status,
        "order_id": str(order_id)
    }
    
    logger.info(f"Sending payment webhook to {webhook_url}")
    logger.info(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        # Add optional signature header for production-like testing
        headers = {
            "Content-Type": "application/json",
        }
        
        # Send the webhook request
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        
        # Check response
        if response.status_code == 200:
            logger.info(f"Webhook successfully sent! Response: {response.text}")
            return True
        else:
            logger.error(f"Failed to send webhook. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending webhook: {e}")
        return False

def main():
    """Main function to parse arguments and send webhook"""
    parser = argparse.ArgumentParser(description="Test payment webhook for As Bolsyn")
    
    parser.add_argument("--url", required=True, help="Webhook URL (include /payment-webhook)")
    parser.add_argument("--order-id", required=True, help="Order ID to update")
    parser.add_argument("--payment-id", default="test_payment_123", help="Payment ID (default: test_payment_123)")
    parser.add_argument("--status", default="completed", choices=["completed", "pending", "failed"], 
                        help="Payment status (default: completed)")
    
    args = parser.parse_args()
    
    # Send the webhook
    success = send_test_webhook(
        webhook_url=args.url,
        order_id=args.order_id,
        payment_id=args.payment_id,
        status=args.status
    )
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 