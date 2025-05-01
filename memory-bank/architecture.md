# As Bolsyn - Architecture Documentation

## Project Structure

```
as-bolsyn/
├── memory-bank/                # Documentation and project tracking
├── src/                        # Source code directory
│   ├── __init__.py             # Package initialization
│   ├── bot.py                  # Main bot entry point and handlers
│   ├── config.py               # Configuration and environment variables
│   ├── db.py                   # Database connection utilities
│   └── models.py               # Database models (Tortoise ORM)
├── tests/                      # Test directory
│   ├── __init__.py             # Test package initialization
│   └── test_bot.py             # Basic structure tests
├── .env.example                # Template for environment variables
├── .gitignore                  # Git ignore file
├── README.md                   # Project documentation
└── requirements.txt            # Python dependencies
```

## Component Overview

### Configuration (`src/config.py`)
Handles loading environment variables using `python-dotenv`. Provides centralized access to:
- Telegram Bot token
- Database connection parameters
- Admin chat ID for notifications
- Default language settings

### Database Models (`src/models.py`)
Uses Tortoise ORM to define the database schema:

1. **Vendor Model**
   - Represents food businesses selling leftover meals
   - Fields: telegram_id, name, contact_phone, status
   - Status can be: pending, approved, rejected

2. **Consumer Model**
   - Represents users who purchase meals
   - Fields: telegram_id

3. **Meal Model**
   - Represents food items listed by vendors
   - Fields: name, description, price, quantity, pickup times, location

4. **Order Model**
   - Represents purchases made by consumers
   - Fields: status, payment_id
   - Status can be: pending, paid, completed, cancelled

### Database Connection (`src/db.py`)
Handles initializing and closing database connections using Tortoise ORM.

### Bot Implementation (`src/bot.py`)
Uses aiogram framework for implementing the Telegram bot:
- Implements command handlers (/start, /help)
- Automatically registers consumers
- Uses Russian text templates
- Initializes database connection on startup
