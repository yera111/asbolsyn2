# Testing Webhooks in Development with ngrok

## Overview
This guide shows how to test the webhook functionality of the As Bolsyn Telegram bot in a development environment using ngrok.

## Step 1: Install ngrok
If you haven't already, install ngrok from https://ngrok.com/download

## Step 2: Start the tunnel
Start an ngrok tunnel pointing to your local server port (default is 8000):

```
ngrok http 8000
```

This will give you a publicly accessible URL like `https://a1b2c3d4.ngrok-free.app`

## Step 3: Update your .env file
Create or modify your `.env` file with the following settings:

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

# SSL Configuration (not needed with ngrok as it provides SSL)
USE_SSL=False

# Security Configuration
RATE_LIMIT_GENERAL=5
RATE_LIMIT_REGISTER=2
RATE_LIMIT_ADD_MEAL=5
RATE_LIMIT_PAYMENT=3
WEBHOOK_RATE_LIMIT=30

# Payment Gateway Settings
PAYMENT_GATEWAY_ENABLED=True
PAYMENT_GATEWAY_API_KEY=your_payment_gateway_api_key_here
PAYMENT_GATEWAY_SECRET=your_payment_gateway_secret_here
PAYMENT_GATEWAY_URL=https://your-payment-gateway-url.com
PAYMENT_WEBHOOK_SECRET=your_webhook_secret_here
PAYMENT_SUCCESS_URL=https://t.me/your_bot_username
PAYMENT_FAILURE_URL=https://t.me/your_bot_username
```

Make sure to replace `your-ngrok-url.ngrok-free.app` with your actual ngrok URL.

## Step 4: Start the application in webhook mode
Start the application using:

```
python run_dev.py
```

The application will start in webhook mode and register with the Telegram API using the ngrok URL.

## Step 5: Testing payment webhooks
You can test payment webhooks by sending POST requests to `https://your-ngrok-url.ngrok-free.app/payment-webhook`.

Example webhook payload:
```json
{
  "payment_id": "12345",
  "status": "completed",
  "order_id": "1"
}
```

You can use tools like Postman, curl, or the ngrok web interface (http://localhost:4040) to inspect and replay webhook requests.

Example curl command:
```
curl -X POST https://your-ngrok-url.ngrok-free.app/payment-webhook \
  -H "Content-Type: application/json" \
  -d '{"payment_id": "12345", "status": "completed", "order_id": "1"}'
```

## Important Notes

1. **Temporary URLs**: ngrok URLs change every time you restart ngrok (unless you have a paid plan). Remember to update your .env file with the new URL each time.

2. **Telegram Bot API**: When testing with Telegram, you need to make sure your bot is set up correctly with the new webhook URL each time.

3. **Reset Webhook**: If you want to switch back to polling mode, set `WEBHOOK_MODE=False` in your .env file and restart the application. This will delete the webhook from Telegram.

4. **Webhook Inspection**: Use the ngrok web interface at http://localhost:4040 to inspect all webhook requests and responses.

5. **Database Testing**: Make sure your database is set up and running correctly for local testing. 