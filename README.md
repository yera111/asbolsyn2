# As Bolsyn - Telegram Bot

A service connecting food businesses with consumers via a Telegram bot to sell specific leftover meals at a discounted price.

## Deployment to Railway

### Prerequisites

1. Create an account on [Railway](https://railway.app/)
2. Install the Railway CLI:
   ```
   npm i -g @railway/cli
   ```
3. Login to Railway:
   ```
   railway login
   ```

### Setup Environment Variables

Set up the following environment variables in Railway:

- `BOT_TOKEN`: Your Telegram bot token (from BotFather)
- `ADMIN_CHAT_ID`: The Telegram chat ID of the admin
- `WEBHOOK_MODE`: Set to "True" for production
- `WEBHOOK_HOST`: Your application URL (e.g., https://your-app-name.railway.app)
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`: Database connection details
- `PAYMENT_GATEWAY_API_KEY`, `PAYMENT_GATEWAY_SECRET`: (If applicable) Your payment gateway credentials

### Deploy to Railway

1. Link your project:
   ```
   railway link
   ```

2. Deploy the application:
   ```
   railway up
   ```

3. Open the project in the Railway dashboard:
   ```
   railway open
   ```

4. Verify that the application is running and the bot is responding

## Local Development

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Create a `.env` file with the necessary environment variables (see `.env.example`)

3. Run the bot in polling mode:
   ```
   python run_dev.py
   ```

## Timezone Issues

Make sure your database and application server are configured to use the Asia/Almaty timezone (UTC+6) to ensure all datetime operations work correctly.

## Setup Instructions

### Local Development

1. Clone this repository
2. Install the required dependencies:
   ```