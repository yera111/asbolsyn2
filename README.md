# As Bolsyn - Telegram Bot

A Telegram bot connecting food businesses with consumers to sell specific leftover meals at a discounted price.

## Setup Instructions

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
5. Run the bot:
   ```
   python -m src.bot
   ```

## Features

- **For Vendors**: Register, list specific leftover meals with details (description, price, quantity, pickup time/location)
- **For Consumers**: Browse meals, find meals nearby, view details, and purchase through integrated payment system

## Development

This project uses:
- Python 3
- aiogram (Telegram Bot Framework)
- PostgreSQL with Tortoise ORM
- Asyncio for asynchronous operations
