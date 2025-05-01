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
│   ├── test_bot.py             # Basic structure tests
│   ├── test_vendor_registration.py # Vendor registration tests
│   ├── test_meal_creation.py   # Meal creation tests
│   └── test_browse_meals.py    # Consumer browse meals tests
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
   - Location includes: address text, latitude, longitude
   - Has is_active flag for soft deletion

4. **Order Model**
   - Represents purchases made by consumers
   - Fields: status, payment_id
   - Status can be: pending, paid, completed, cancelled

### Database Connection (`src/db.py`)
Handles initializing and closing database connections using Tortoise ORM.

### Bot Implementation (`src/bot.py`)
Uses aiogram framework for implementing the Telegram bot:
- Implements command handlers (/start, /help, /register_vendor, /add_meal, /my_meals, /delete_meal, /browse_meals)
- Provides an intuitive keyboard menu for common functions
- Uses button handlers to respond to menu interactions
- Automatically registers consumers
- Implements Finite State Machine (FSM) for vendor registration and meal creation flows
- Implements vendor approval/rejection process
- Implements meal management functionality
- Implements consumer browse functionality
- Uses Russian text templates
- Initializes database connection on startup

## User Interface

The bot provides a user-friendly interface through:

1. **Keyboard Menu**
   - Accessible via the /start command
   - Includes buttons for browsing meals, finding nearby meals, vendor registration, and help
   - Buttons trigger the same functionality as their corresponding commands
   - Makes the bot more accessible to users unfamiliar with Telegram commands

2. **Welcome Message**
   - Provides a clear introduction to the bot's purpose
   - Includes brief instructions on available features
   - Guides users to use the keyboard menu or commands

3. **Command System**
   - Traditional Telegram commands (/start, /help, etc.)
   - Available for users who prefer text commands

## Vendor Registration Process

The vendor registration process is implemented using aiogram's Finite State Machine:

1. **Registration Initiation**
   - User sends `/register_vendor` command
   - System checks if user is already registered as a vendor
   - If not, starts the registration process by setting state to `VendorRegistration.waiting_for_name`

2. **Data Collection**
   - System prompts for vendor name (state: `VendorRegistration.waiting_for_name`)
   - System collects name and prompts for contact phone (state: `VendorRegistration.waiting_for_phone`)
   - System collects phone number and completes registration

3. **Vendor Status Management**
   - New vendors are created with "pending" status
   - Admin is notified about new registration with approve/reject options
   - Admin can use `/approve_vendor <telegram_id>` or `/reject_vendor <telegram_id>` commands
   - Vendor is notified about approval/rejection

4. **Security Measures**
   - Only users with admin privileges can approve/reject vendors
   - Vendor status verification is performed before allowing meal listings

## Meal Creation Process

The meal creation process is implemented using aiogram's Finite State Machine:

1. **Creation Initiation**
   - Vendor sends `/add_meal` command
   - System checks if user is a registered and approved vendor
   - If yes, starts the meal creation process by setting state to `MealCreation.waiting_for_name`

2. **Basic Information Collection**
   - System collects meal name (state: `MealCreation.waiting_for_name`)
   - System collects description (state: `MealCreation.waiting_for_description`)
   - System collects price with validation (state: `MealCreation.waiting_for_price`)
   - System collects quantity with validation (state: `MealCreation.waiting_for_quantity`)

3. **Time Information Collection**
   - System collects pickup start time with format validation (state: `MealCreation.waiting_for_pickup_start`)
   - System collects pickup end time with format and logic validation (state: `MealCreation.waiting_for_pickup_end`)

4. **Location Information Collection**
   - System collects text address (state: `MealCreation.waiting_for_location_address`)
   - System prompts for geographical coordinates using Telegram's location sharing (state: `MealCreation.waiting_for_location_coords`)
   - System stores both address and coordinates for future search functionality

5. **Data Storage**
   - System creates a new Meal record with collected information
   - System associates the meal with the vendor
   - System confirms successful creation to the vendor

## Meal Management

Vendors can manage their meal listings using the following functions:

1. **View Meals**
   - Vendor sends `/my_meals` command
   - System retrieves and displays all active meals for the vendor
   - Display includes key information: name, price, quantity, pickup times

2. **Delete Meals**
   - Vendor sends `/delete_meal <id>` command 
   - System verifies the meal exists and belongs to the vendor
   - System performs a soft delete by setting is_active to false
   - System preserves meal record for completed orders

## Consumer Features

The consumer functionality is implemented with the following features:

1. **Browse Meals**
   - Consumer sends `/browse_meals` command
   - System automatically registers the user as a consumer if not already registered
   - System retrieves all active meals with quantity > 0, ordered by most recent first
   - System displays a formatted list of available meals with essential details:
     - Meal name
     - Price
     - Vendor name
     - Available quantity
     - Pickup time window
   - If no meals are available, the system informs the user

2. **Filter Meals Nearby**
   - Consumer sends `/meals_nearby` command
   - System automatically registers the user as a consumer if not already registered
   - System prompts user to share their location using Telegram's native location sharing
   - System uses Haversine formula to calculate distance between user and meal pickup locations
   - System filters meals to only show those within a 10km radius
   - System sorts meals by proximity (closest first)
   - System displays a formatted list of nearby meals with essential details:
     - Meal name
     - Price
     - Distance to the meal (in kilometers)
     - Vendor name
     - Available quantity
     - Pickup time window
   - If no meals are available within the radius, the system informs the user

3. **View Meal Details**
   - Consumer sends `/view_meal <id>` command with a specific meal ID
   - System automatically registers the user as a consumer if not already registered
   - System displays detailed information about the meal:
     - Name
     - Description
     - Price
     - Vendor name
     - Available quantity
     - Pickup time window
     - Pickup location address
   - System provides a "Buy" button using Telegram's inline keyboard
   - When user clicks the "Buy" button, system registers the action and shows a placeholder message (payment integration will be implemented in Phase 4)

4. **Future Features**
   - Placing orders
   - Making payments
   - Tracking order status
   - Rating meals/vendors
