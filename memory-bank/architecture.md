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
│   ├── models.py               # Database models (Tortoise ORM)
│   └── metrics.py              # Metrics tracking and reporting
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

5. **Metric Model**
   - Represents tracked events for analytics and MVP hypothesis evaluation
   - Fields: metric_type, value, entity_id, user_id, metadata, timestamp
   - Used for tracking key user interactions throughout the application

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

### Metrics System (`src/metrics.py`)
Implements comprehensive analytics for tracking MVP hypothesis:
- Provides standardized tracking function for recording metrics events
- Implements reporting capabilities for generating analytics dashboards
- Supports conversion funnel analysis (browse → view → order → payment)
- Provides admin-only metrics dashboard via the `/metrics` command
- Tracks key performance indicators aligned with business goals:
  - User acquisition (registrations)
  - Engagement (meal creation, browsing)
  - Conversion (order creation, payment)
  - Sales performance (GMV, completed orders)
- Non-blocking implementation ensures failures don't affect core application flow
- Supports filtering by time period and metric types

## User Interface

The bot provides a user-friendly interface through:

1. **Persistent Keyboard Menu**
   - Accessible throughout the entire user journey
   - Always visible after every interaction with the bot
   - Includes buttons for browsing meals, finding nearby meals, vendor registration, and help
   - Buttons trigger the same functionality as their corresponding commands
   - Makes the bot more accessible to users unfamiliar with Telegram commands

2. **Button Handler System**
   - Each keyboard button has a corresponding message handler function
   - Handler functions are registered using aiogram's message filters:
     ```python
     @dp.message(lambda message: message.text == "📋 Просмотреть блюда")
     async def button_browse_meals(message: Message):
         await cmd_browse_meals(message)
     ```
   - Button handlers delegate to command handlers to maintain consistent behavior
   - Complete coverage ensures all interactive elements respond correctly
   - Main menu buttons with dedicated handlers:
     - "📋 Просмотреть блюда" (Browse Meals) → calls cmd_browse_meals
     - "📍 Блюда поблизости" (Nearby Meals) → calls cmd_meals_nearby
     - "🛒 Мои заказы" (My Orders) → calls cmd_my_orders
     - "🏪 Зарегистрироваться как поставщик" (Register as Vendor) → calls cmd_register_vendor
     - "❓ Помощь" (Help) → calls cmd_help

3. **Welcome Message**
   - Provides a clear introduction to the bot's purpose
   - Includes brief instructions on available features
   - Guides users to use the keyboard menu or commands

4. **Command System**
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
   - System maintains distance information throughout the filtering process for display
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

3. **Payment URL Generation**
   - Uses a resilient approach with fallback values for all configuration
   - Ensures valid HTTP URLs even when environment variables are missing
   - Includes order ID and amount in payment URL for tracking
   - Provides success and failure redirect URLs back to the bot
   - Uses URL validation to prevent Telegram API errors
   - Configurable for different payment providers through environment variables
   - Has sensible defaults for development and testing environments

4. **Payment Confirmation**
   - Payment provider sends a webhook notification to the bot
   - System verifies the webhook signature for security
   - System retrieves the associated order using the payment ID
   - System updates order status to "paid"
   - System decreases the meal's available quantity
   - System sends confirmation notifications

5. **Payment Simulation**
   - For development and testing, the MVP includes a simulated payment flow
   - Simulated webhooks are generated automatically after a short delay
   - This allows testing the full payment flow without a live payment provider
   - Configuration options allow easy switching between simulation and real providers

6. **Error Handling**
   - System handles various error scenarios:
     - Meal no longer available
     - Insufficient quantity
     - Payment gateway errors
     - Webhook processing failures
   - Provides clear error messages to users
   - Logs detailed error information for debugging

## Database Migration System

The application includes a simple database migration system to handle schema evolution:

1. **Schema Validation**
   - When the application starts, it checks the database schema
   - Verifies that required tables and columns exist
   - Automatically adds missing columns when needed
   - Preserves existing data during migrations

2. **Testing Support**
   - Uses in-memory SQLite for automated testing
   - Provides fixture utilities to set up clean test environments
   - Simulates environment variables needed for testing
   - Prevents test isolation issues with automatic cleanup

## Testing Architecture

The application uses a comprehensive testing strategy:

1. **Unit Tests**
   - Test individual components in isolation
   - Mock external dependencies for predictable results
   - Cover critical path functionality like payment processing

2. **Integration Tests**
   - Test interactions between components 
   - Verify database operations work correctly
   - Test end-to-end flows like meal purchase and payment

3. **Test Configuration**
   - Uses pytest and pytest-asyncio for asynchronous testing
   - Sets up appropriate test fixtures for database and payment testing
   - Simulates environment variables for consistent test execution

4. **Test Database**
   - Uses in-memory SQLite for fast test execution
   - Automatically creates required schema for each test
   - Cleans up after tests to prevent state leakage

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
   - Confirmation of meal pickup
      Approved suppliers can confirm the fact of receipt of the order by the buyer with the command
      /complete_order <id>. The bot checks the order ownership, that the status = PAID, then transfers it to COMPLETED, fills in completed_at and sends notifications to the supplier and the buyer.

3. **Subscription Options**
   - Allow consumers to subscribe to favorite vendors
   - Send notifications when new meals are listed by subscribed vendors
   - Implement loyalty rewards for repeat customers

## Deployment Architecture

The application is designed to be deployed to a Platform-as-a-Service (PaaS) provider, with the following key components:

1. **Web Service**
   - Deployed as a web service on a PaaS platform (e.g., Render)
   - Supports both development (polling) and production (webhook) modes
   - Uses gunicorn as a production-ready WSGI server
   - Handles payment gateway webhooks for transaction confirmation

2. **Database Service**
   - Uses PostgreSQL as a managed database service
   - Connects using environment variables for secure credential management
   - Scalable database design to handle growing user base
   - Includes indexes on frequently queried fields for performance

3. **Webhook Configuration**
   - Uses Telegram webhooks in production for efficient message handling
   - Configurable webhook URL and path
   - Integrated with aiohttp for asynchronous HTTP request handling
   - Includes separate endpoint for payment webhooks

4. **Environment Variable Management**
   - All configuration parameters stored as environment variables
   - Includes sensible defaults for local development
   - Separates development and production configurations
   - Uses python-dotenv for local development environment

5. **Security Considerations**
   - HTTPS enforcement for all webhook endpoints
   - Payment webhook signature verification
   - Database credentials stored as secure environment variables
   - Admin authentication for privileged operations

### Deployment Workflow

The deployment workflow follows these steps:

1. **Development**
   - Local development using polling mode
   - Test database using SQLite in-memory for rapid testing
   - Run using `run_dev.py` script

2. **Production Preparation**
   - Configuration of environment variables on PaaS provider
   - Setting up PostgreSQL database instance
   - Setting webhook mode to True for production environment

3. **Deployment Process**
   - Automatic deployment from GitHub repository
   - Build process installs dependencies from requirements.txt
   - Application starts using gunicorn and the wsgi.py entry point
   - Webhook automatically configured on application startup

4. **Monitoring & Maintenance**
   - Logging configured for production environment
   - Error handling for webhook processing
   - Graceful shutdown procedures to maintain database integrity

## End-to-End Testing Approach

The application includes a comprehensive end-to-end testing framework to validate all functionality in the production environment:

1. **Test Framework Structure**
   - `scripts/e2e_test.py`: Structured test script that guides through all test scenarios
   - `scripts/setup_test_data.py`: Tool for configuring test accounts and credentials
   - `docs/e2e_testing_guide.md`: Detailed documentation of the testing process

2. **Test Scenarios**
   - Vendor registration and approval flow
   - Meal creation and management
   - Consumer browse and purchase
   - Payment and order fulfillment
   - Nearby meal search functionality
   - Order history verification

3. **Testing Methodology**
   - Manual testing guided by structured script
   - Detailed step-by-step instructions
   - Clear expected outcomes
   - Comprehensive logging for test results
   - Test reports to track testing progress

4. **Test Data Management**
   - Configurable test accounts for consistent testing
   - Test payment credentials integration
   - Test location coordinates for Almaty
   - Standard test meal configurations

5. **Production Validation**
   - Pre-launch validation checklist
   - Language verification (Russian)
   - Error handling verification
   - Full flow verification from vendor registration to consumer purchase
   - Payment confirmation and notification testing

6. **Testing Tools Integration**
   - Logging framework for test results
   - Structured test step organization
   - Configuration file generation for repeatability
   - Environment-specific testing parameters

## Timezone Handling

The application uses proper timezone handling to ensure that all datetime operations are consistent and user-friendly:

1. **Timezone Configuration**
   - Configured "Asia/Almaty" timezone (UTC+6) as the base timezone for the application
   - All timestamps are stored and processed in this timezone
   - Ensures meal pickup times are correctly displayed and filtered

2. **Timezone Utility Functions**
   - `get_current_almaty_time()`: Returns the current time in Almaty timezone
   - `to_almaty_time(dt)`: Converts any datetime to Almaty timezone
   - `ensure_timezone_aware(dt)`: Makes naive datetimes timezone-aware
   - `format_pickup_time(dt)`: Formats datetimes for display

3. **Cross-Midnight Pickup Windows**
   - System correctly handles pickup windows that cross midnight
   - When end time is earlier than start time, it's automatically adjusted to the next day
   - Ensures proper functioning for evening/night pickup times (e.g., from 23:30 to 02:30)

## Meal Expiration Management

The application implements automatic management of expired meals:

1. **Background Task for Deactivation**
   - A periodic task checks for meals with passed pickup windows
   - Runs every 10 minutes in the background
   - Automatically deactivates expired meals by setting `is_active=False`
   - Logs all deactivation events for troubleshooting

2. **Expired Meal Filtering**
   - All meal browsing and search functions filter out expired meals
   - Uses current Almaty time for comparisons
   - Prevents users from seeing or purchasing meals past their pickup window
   - Ensures consistent handling across all meal-related operations

3. **Timezone-Aware Queries**
   - Database queries use timezone-aware datetime comparisons
   - All expiration checks consider the Almaty timezone
   - Consistent filtering throughout the application

## Metrics & Analytics System

The application includes a comprehensive metrics system to track key performance indicators (KPIs) and evaluate the success of the MVP hypothesis:

1. **Database Schema**
   - `Metric` model stores individual metric events with the following fields:
     - `metric_type`: Categorizes the metric (user registration, meal view, order paid, etc.)
     - `value`: Numeric value associated with the event (default 1.0 for counts)
     - `entity_id`: Optional ID of the related entity (meal, order, etc.)
     - `user_id`: Optional Telegram user ID to track user behavior
     - `metadata`: JSON field for additional contextual data
     - `timestamp`: When the metric was recorded (timezone-aware)

2. **Metric Types**
   - User acquisition metrics: `USER_REGISTRATION`, `VENDOR_REGISTRATION`, `VENDOR_APPROVAL`
   - Engagement metrics: `MEAL_CREATION`, `MEAL_BROWSE`, `MEAL_VIEW`, `NEARBY_SEARCH`
   - Conversion metrics: `ORDER_CREATED`, `ORDER_PAID`, `ORDER_COMPLETED`, `ORDER_CANCELLED`
   - Behavioral metrics: `PORTION_SELECTION` for tracking order sizing preferences

3. **Tracking Implementation**
   - `track_metric()` function provides a standardized way to record metrics
   - Non-blocking implementation ensures failures don't affect core application flow
   - Detailed error logging for troubleshooting
   - Automatic metadata collection for rich context

4. **Reporting Capabilities**
   - `get_metrics_report()` generates comprehensive reports with:
     - Event counts by type
     - Conversion rates (browse → view → order → payment)
     - User acquisition statistics
     - Engagement metrics (meals per vendor, average order value)
     - Transaction metrics (sales per day)
   - Time-based filtering allows for period comparisons
   - Custom metric type filtering for targeted analysis

5. **Dashboard for Administrators**
   - Admin-only `/metrics` command provides real-time access to key metrics
   - Overview section shows high-level performance indicators
   - Weekly conversion rates to identify funnel bottlenecks
   - Aggregated statistics on users, vendors, meals, and orders
   - Gross Merchandise Value (GMV) calculation

6. **Strategic Metrics Alignment**
   The metrics system is designed to answer key business questions from the [Game Design Document](game-design-document.md):
   - User Acquisition: How many users and vendors are onboarding?
   - Engagement: How many meals are vendors listing per week?
   - Sales Performance: How many meals are sold and what is the conversion rate?
   - Revenue: What is the total GMV transacted through the platform?
   - Retention: Are vendors continuing to list meals after initial registration?

7. **Integration Points**
   Metrics are recorded at key points in the user journey:
   - When users first interact with the bot
   - During vendor registration and approval
   - When meals are created by vendors
   - During meal browsing and detailed viewing
   - Throughout the order and payment process
   - During special interactions like nearby search

8. **Future Extensions**
   The metrics system is designed for extensibility:
   - Additional metric types can be easily added
   - The reporting system can accommodate new analysis requirements
   - The underlying database schema supports detailed drill-down analysis
   - The framework supports future visualization integrations
