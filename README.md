# As Bolsyn - Telegram Bot

A Telegram bot connecting food businesses with consumers to sell specific leftover meals at a discounted price.

## Setup Instructions

### Local Development

1. Clone this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Copy `env.example` to `.env` and fill in your configuration:
   ```
   cp env.example .env
   ```
4. Edit the `.env` file with your Telegram Bot token and database credentials
5. Run the bot in development mode:
   ```
   python run_dev.py
   ```

### Production Deployment

#### Render

1. Fork or clone this repository to your GitHub account
2. Go to your Render dashboard and create a new Web Service
3. Connect your GitHub repository
4. Use the following settings:
   - **Name**: as-bolsyn-bot (or your preferred name)
   - **Environment**: Python
   - **Region**: Choose the region closest to Kazakhstan
   - **Branch**: main (or your default branch)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn wsgi:application`
5. Add the following environment variables:
   - `BOT_TOKEN`: Your Telegram bot token
   - `WEBHOOK_MODE`: `True`
   - `WEBHOOK_HOST`: Your Render app URL (e.g., https://as-bolsyn-bot.onrender.com)
   - `WEBHOOK_PATH`: `/webhook`
   - `DB_HOST`: Your database host
   - `DB_PORT`: Your database port
   - `DB_NAME`: Your database name
   - `DB_USER`: Your database user
   - `DB_PASSWORD`: Your database password
   - `ADMIN_CHAT_ID`: Your Telegram chat ID for admin notifications
   - `PAYMENT_GATEWAY_ENABLED`: `True`
   - `PAYMENT_GATEWAY_API_KEY`: Your payment gateway API key
   - `PAYMENT_GATEWAY_SECRET`: Your payment gateway secret
   - `PAYMENT_GATEWAY_URL`: Your payment gateway URL
   - `PAYMENT_WEBHOOK_SECRET`: Your payment webhook secret
   - `PAYMENT_SUCCESS_URL`: Your success URL
   - `PAYMENT_FAILURE_URL`: Your failure URL
6. Click "Create Web Service"

#### Database Setup

1. Create a PostgreSQL database instance (you can use Render's PostgreSQL service)
2. Configure the database connection parameters in your environment variables

## Features

- **For Vendors**: Register, list specific leftover meals with details (description, price, quantity, pickup time/location)
- **For Consumers**: Browse meals, find meals nearby, view details, and purchase through integrated payment system

## Development

This project uses:
- Python 3
- aiogram (Telegram Bot Framework)
- PostgreSQL with Tortoise ORM
- Asyncio for asynchronous operations
- Webhook for production deployment

## Architecture

This bot follows a clean architecture pattern with:

1. **Configuration** (`src/config.py`): Centralized configuration management
2. **Database Models** (`src/models.py`): Data structures using Tortoise ORM
3. **Database Connection** (`src/db.py`): Database initialization and connection handling
4. **Payment Gateway** (`src/payment.py`): Payment processing integration
5. **Bot Logic** (`src/bot.py`): Core bot functionality and handlers
6. **Web Server** (`src/main.py`): Webhook handling for production deployment

## Testing

### End-to-End Testing

For comprehensive testing of the deployed application:

1. Configure test data:
   ```
   python scripts/setup_test_data.py
   ```

2. Run the end-to-end test script:
   ```
   python scripts/e2e_test.py
   ```

This will guide you through testing all major functionality of the bot including:
- Vendor registration and approval
- Meal creation and management
- Consumer browsing and purchasing
- Payment processing
- Order notifications and history

### Documentation

For more information about testing:
- `docs/e2e_testing_guide.md`: Complete guide to end-to-end testing
- `scripts/README.md`: Description of available testing scripts
- `docs/sample_test_results.md`: Example of test result format
