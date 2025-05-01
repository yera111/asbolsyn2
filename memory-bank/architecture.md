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

1. **Persistent Keyboard Menu**
   - Accessible throughout the entire user journey
   - Always visible after every interaction with the bot
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
   - Consumer sends `/browse_meals` command or uses the corresponding menu button
   - System automatically registers the user as a consumer if not already registered
   - System retrieves all active meals with quantity > 0, ordered by most recent first
   - System displays each meal as a separate message with its own "View" button
   - Each meal display includes essential details:
     - Meal name
     - Price
     - Vendor name
     - Available quantity
     - Pickup time window
   - If no meals are available, the system informs the user

2. **Filter Meals Nearby**
   - Consumer sends `/meals_nearby` command or uses the corresponding menu button
   - System automatically registers the user as a consumer if not already registered
   - System prompts user to share their location using Telegram's native location sharing
   - System uses Haversine formula to calculate distance between user and meal pickup locations
   - System filters meals to only show those within a 10km radius
   - System sorts meals by proximity (closest first)
   - System displays each nearby meal as a separate message with its own "View" button
   - Each meal display includes essential details:
     - Meal name
     - Price
     - Distance to the meal (in kilometers)
     - Vendor name
     - Available quantity
     - Pickup time window
   - If no meals are available within the radius, the system informs the user

3. **View Meal Details and Select Portions**
   - Consumer clicks "View" button on a meal or uses `/view_meal <id>` command
   - System automatically registers the user as a consumer if not already registered
   - System displays detailed information about the meal:
     - Name
     - Description
     - Price
     - Vendor name
     - Available quantity
     - Pickup time window
     - Pickup location address
   - System provides portion selection buttons (1-5, limited by available quantity)
   - User selects desired number of portions
   - System calculates and displays total price based on selected portions
   - System provides a "Buy" button for final purchase confirmation

4. **Payment & Order Process**
   - Consumer clicks "Buy" button after selecting portions
   - System validates meal availability and portion quantity
   - System creates a new Order record with status "pending"
   - System calls the payment gateway to create a payment
   - System displays payment link to user via inline button
   - User completes payment through the payment gateway
   - Payment gateway sends a webhook notification upon completion
   - System processes the webhook and updates order status to "paid"
   - System decreases the meal's available quantity
   - System sends confirmation notifications to both consumer and vendor

5. **Order Tracking**
   - Consumer can view their order history using `/my_orders` command or the "My Orders" button
   - System displays a list of all orders with their status and details
   - Each order shows:
     - Order ID
     - Meal name
     - Ordered quantity
     - Order status (Pending, Paid, Completed, Cancelled)
     - Order date/time

## Payment Gateway Integration

The payment integration is implemented using a flexible gateway approach:

1. **Payment Gateway Module**
   - Implemented as a separate module for clear separation of concerns
   - Provides a common interface that can be adapted to different payment providers
   - Handles payment creation, verification, and webhook processing
   - For the MVP, includes a simulated payment flow for testing

2. **Payment Creation Flow**
   - When user confirms purchase, system creates a pending order
   - System calls the payment gateway to generate a payment ID and URL
   - System associates the payment ID with the order
   - System presents payment URL to user via Telegram inline button
   - User is redirected to the payment provider's page to complete payment

3. **Payment Confirmation**
   - Payment provider sends a webhook notification to the bot
   - System verifies the webhook signature for security
   - System retrieves the associated order using the payment ID
   - System updates order status to "paid"
   - System decreases the meal's available quantity
   - System sends confirmation notifications

4. **Payment Simulation**
   - For development and testing, the MVP includes a simulated payment flow
   - Simulated webhooks are generated automatically after a short delay
   - This allows testing the full payment flow without a live payment provider
   - Configuration options allow easy switching between simulation and real providers

5. **Error Handling**
   - System handles various error scenarios:
     - Meal no longer available
     - Insufficient quantity
     - Payment gateway errors
     - Webhook processing failures
   - Provides clear error messages to users
   - Logs detailed error information for debugging

## Future Features

Planned features for future phases include:

1. **Rating System**
   - Allow consumers to rate meals and vendors after pickup
   - Display average ratings on meal listings
   - Implement a feedback system for quality improvement

2. **Enhanced Order Management**
   - Add order status updates (preparing, ready for pickup, completed)
   - Implement order cancellation with refund handling
   - Add order reminders as pickup time approaches

3. **Subscription Options**
   - Allow consumers to subscribe to favorite vendors
   - Send notifications when new meals are listed by subscribed vendors
   - Implement loyalty rewards for repeat customers
