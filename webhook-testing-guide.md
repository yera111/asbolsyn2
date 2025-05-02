# Webhook Testing Guide for As Bolsyn Telegram Bot

This guide provides step-by-step instructions for testing webhook functionality in the As Bolsyn Telegram Bot during development.

## Prerequisites

- Python 3.8+ installed
- PostgreSQL database running
- Ngrok installed (https://ngrok.com/download)
- Telegram Bot Token (obtain from BotFather in Telegram)

## Part 1: Setting Up Ngrok

1. **Start ngrok**: Open a terminal window and start ngrok pointing to port 8000:
   ```
   ngrok http 8000
   ```

2. **Note the ngrok URL**: Ngrok will provide a URL like `https://a1b2c3d4.ngrok-free.app`. Copy this URL for use in the next steps.

## Part 2: Configure Application for Webhook Mode

1. **Create or update your .env file**: Use the following template, replacing placeholders with your actual values:
   ```
   # Telegram Bot credentials
   BOT_TOKEN=your_telegram_bot_token_here
   
   # Database settings
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=asbolsyn
   DB_USER=postgres
   DB_PASSWORD=your_db_password_here
   
   # Admin Chat ID for notifications
   ADMIN_CHAT_ID=your_admin_chat_id_here
   
   # Webhook settings (for development testing with ngrok)
   WEBHOOK_MODE=True
   WEBHOOK_HOST=https://your-ngrok-url.ngrok-free.app
   WEBHOOK_PATH=/webhook
   WEBAPP_HOST=0.0.0.0
   WEBAPP_PORT=8000
   
   # SSL Configuration (not needed with ngrok)
   USE_SSL=False
   
   # Payment Gateway Settings
   PAYMENT_GATEWAY_ENABLED=True
   PAYMENT_GATEWAY_API_KEY=your_payment_gateway_api_key_here
   PAYMENT_GATEWAY_SECRET=your_payment_gateway_secret_here
   PAYMENT_GATEWAY_URL=https://your-payment-gateway-url.com
   PAYMENT_WEBHOOK_SECRET=your_webhook_secret_here
   PAYMENT_SUCCESS_URL=https://t.me/your_bot_username
   PAYMENT_FAILURE_URL=https://t.me/your_bot_username
   ```

   Ensure you replace `https://your-ngrok-url.ngrok-free.app` with your actual ngrok URL.

2. **Install dependencies**: If not already installed, install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

## Part 3: Start the Application in Webhook Mode

1. **Run the application**: Start the application in webhook mode:
   ```
   python run_dev.py
   ```

2. **Verify webhook setup**: Check the application logs for a message like:
   ```
   Webhook set to: https://your-ngrok-url.ngrok-free.app/webhook
   ```

## Part 4: Testing Telegram Webhook

1. **Interact with your bot**: Open Telegram, search for your bot, and send a message like `/start`.

2. **Verify webhook reception**: Watch your application logs to confirm that the bot receives the webhook from Telegram.

3. **Check ngrok interface**: Open `http://localhost:4040` in your browser to see detailed information about incoming webhook requests from Telegram.

## Part 5: Testing Payment Webhooks

To test payment webhooks, you'll need to:

1. **Create a test order**: Interact with your bot to create a meal and place an order. Note the order ID from your logs or database.

2. **Send a test payment webhook**: Use the provided script `test_payment_webhook.py` to send a webhook:
   ```
   python test_payment_webhook.py --url https://your-ngrok-url.ngrok-free.app/payment-webhook --order-id 1
   ```

   Replace `1` with your actual order ID.

3. **Verify webhook processing**: Watch your application logs to confirm that the webhook was processed successfully:
   ```
   INFO:root:Processing payment webhook for order 1
   INFO:root:Order 1 marked as paid with payment test_payment_123
   ```

4. **Check order status**: Verify in your application or database that the order status has changed to `PAID`.

5. **Test different status values**: You can test different payment statuses:
   ```
   python test_payment_webhook.py --url https://your-ngrok-url.ngrok-free.app/payment-webhook --order-id 1 --status pending
   ```

## Part 6: Webhook Debugging

If you encounter issues with webhook processing:

1. **Check ngrok logs**: The ngrok web interface at `http://localhost:4040` shows complete request and response details.

2. **Verify order existence**: Ensure the order ID you're using in test webhooks actually exists in your database.

3. **Check application logs**: Look for error messages in your application logs.

4. **Test webhook URL directly**: Use curl to send a test request:
   ```
   curl -X POST https://your-ngrok-url.ngrok-free.app/payment-webhook \
     -H "Content-Type: application/json" \
     -d '{"payment_id": "test_payment_123", "status": "completed", "order_id": "1"}'
   ```

## Part 7: Switching Back to Polling Mode

When you've finished testing with webhooks:

1. **Stop the application**: Press Ctrl+C to stop the running application.

2. **Update .env file**: Set `WEBHOOK_MODE=False` in your .env file.

3. **Restart in polling mode**: Run `python run_dev.py` again.

4. **Verify webhook removal**: Check the logs for a message indicating the webhook was removed:
   ```
   Webhook removed
   ```

## Common Issues and Solutions

1. **Webhook not receiving messages**:
   - Check that your ngrok URL is correct in the .env file
   - Verify that `WEBHOOK_MODE=True` is set
   - Make sure the application correctly started in webhook mode
   - Check ngrok logs for any errors

2. **Payment webhook failures**:
   - Verify the order ID exists in your database
   - Check application logs for error messages
   - Ensure the webhook URL is correct

3. **Ngrok URL changed**:
   - Ngrok URLs change each time you restart ngrok (unless you have a paid plan)
   - Always update your .env file with the new URL
   - Restart the application after updating the URL

4. **Database connection issues**:
   - Verify your PostgreSQL database is running
   - Check DB_* environment variables in your .env file

## Advanced: Using a Signature with Webhooks

For more production-like testing, you can add signature verification:

1. **Add signature header to requests**: Update the test_payment_webhook.py script:
   ```python
   import hmac
   import hashlib
   
   # Add to send_test_webhook function
   webhook_secret = "your_webhook_secret"
   signature = hmac.new(
       webhook_secret.encode(),
       json.dumps(payload).encode(),
       hashlib.sha256
   ).hexdigest()
   
   headers = {
       "Content-Type": "application/json",
       "X-Signature": signature
   }
   ```

2. **Configure the same secret**: Make sure your .env file has the same PAYMENT_WEBHOOK_SECRET value. 