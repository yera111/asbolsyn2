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
   - System informs user about cancellation options (`/cancel` command or text-based cancellation)

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

6. **Cancellation Support**
   - Users can cancel meal creation at any stage using `/cancel` command
   - Text-based cancellation is supported (users can type "отмена", "отменить", or "cancel")
   - System clears the current state and returns user to main menu
   - Cancellation is available during any step of the meal creation process

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

6. **Order Management**
   - **Order Cancellation**:
     - Admin can cancel stuck orders with the `/cancel_order <id>` command
     - System validates admin credentials before allowing cancellation
     - System updates order status to CANCELLED
     - Both consumer and vendor are notified about cancellation
     - Metrics are tracked for cancelled orders
   - **Order Completion**:
     - Approved vendors can confirm order receipt with the `/complete_order <id>` command
     - The system validates order ownership and that the status is PAID
     - The order is updated to COMPLETED status with completed_at timestamp
     - The buyer receives notification of order completion

## Payment Gateway Integration

The payment integration is implemented using a flexible gateway approach:

1. **Payment Gateway Module**
   - Implemented as a separate module for clear separation of concerns
   - Provides a common interface that can be adapted to different payment providers
   - Handles payment creation, verification, and webhook processing
   - Supports two payment methods:
     - **Telegram's Built-in Payment System**: Primary method when available
     - **External Payment Gateway**: Fallback method when Telegram payments aren't configured

2. **Telegram Payment Integration**
   - Uses Telegram's native payment API for a seamless in-app checkout experience
   - Integrated with Freedom Pay KGS (Kyrgyz sum) as the payment provider
   - Configuration through environment variables:
     - `TELEGRAM_PAYMENT_ENABLED`: Flag to enable/disable Telegram payments
     - `TELEGRAM_PAYMENT_PROVIDER_TOKEN`: Production token from BotFather
     - `TELEGRAM_PAYMENT_TEST_TOKEN`: Test token for development/testing
     - `TELEGRAM_PAYMENT_CURRENCY`: Currency code (default: KGS)
   - Payment flow:
     - User selects meal and quantity, initiating the order creation
     - Bot creates a Telegram invoice with meal details and price
     - Pre-checkout validation ensures meal is still available
     - Successful payment updates the order status and notifies vendor
   - Handlers:
     - `process_pre_checkout_query`: Validates availability before completing payment
     - `process_successful_payment`: Handles successful payment completion

3. **External Payment Gateway (Fallback)**
   - Used when Telegram payments are not available or disabled
   - When user confirms purchase, system creates a pending order
   - System calls the payment gateway to generate a payment ID and URL
   - System associates the payment ID with the order
   - System presents payment URL to user via Telegram inline button
   - User is redirected to the payment provider's page to complete payment

4. **Payment Creation Flow**
   - System checks if Telegram payments are available and configured
   - If available, generates a Telegram invoice with the order details
   - If not available, falls back to the external payment gateway flow
   - Both methods associate a unique payment ID with the order for tracking

5. **Payment URL Generation (External Method)**
   - Uses a resilient approach with fallback values for all configuration
   - Ensures valid HTTP URLs even when environment variables are missing
   - Includes order ID and amount in payment URL for tracking
   - Provides success and failure redirect URLs back to the bot
   - Uses URL validation to prevent Telegram API errors
   - Configurable for different payment providers through environment variables
   - Has sensible defaults for development and testing environments

6. **Payment Confirmation**
   - **Telegram Method**:
     - Bot receives a successful_payment message
     - System retrieves the associated order using the payment payload
     - System updates order status to "paid"
     - System decreases the meal's available quantity
     - System sends confirmation notifications
   - **External Method**:
     - Payment provider sends a webhook notification to the bot
     - System verifies the webhook signature for security
     - System retrieves the associated order using the payment ID
     - System updates order status to "paid"
     - System decreases the meal's available quantity
     - System sends confirmation notifications

7. **Error Handling**
   - System handles various error scenarios:
     - Meal no longer available
     - Insufficient quantity
     - Payment gateway errors
     - Webhook processing failures
     - Pre-checkout validation failures
   - Provides clear error messages to users
   - Logs detailed error information for debugging

8. **Enhanced Payment Validation (Telegram Method)**
   - **Pre-checkout Validation**:
     - Validates payload format and order ID extraction
     - Checks order existence and pending status
     - Verifies meal availability and sufficient quantity
     - Validates pickup time hasn't expired
     - Provides specific error messages for each failure scenario
   - **Successful Payment Processing**:
     - Validates payment payload format
     - Prevents duplicate payment processing
     - Handles missing meal or vendor information gracefully
     - Provides comprehensive error recovery and user feedback
     - Includes detailed logging for debugging payment issues

## Process Cancellation System

The application includes a comprehensive cancellation system that allows users to exit multi-step processes:

1. **Cancellation Commands**
   - `/cancel` command works during any FSM state
   - Text-based cancellation supports "отмена", "отменить", and "cancel"
   - Cancellation is available for all multi-step processes:
     - Meal creation (`MealCreation` states)
     - Vendor registration (`VendorRegistration` states)
     - Nearby meals search (`MealsNearbySearch` states)

2. **Cancellation Behavior**
   - System detects current state and provides appropriate cancellation message
   - State is completely cleared to prevent data leakage
   - User is returned to main menu with keyboard
   - Process-specific cancellation messages inform user what was cancelled

3. **User Experience**
   - Cancellation instructions are provided at the start of multi-step processes
   - Users can cancel at any stage without losing their place in the application
   - Clear feedback confirms what process was cancelled
   - Immediate return to main functionality after cancellation

## Database Migration System

The application includes a comprehensive database migration system using Aerich to handle schema evolution:

1. **Aerich Integration**
   - Uses Aerich, the standard migration tool for Tortoise ORM
   - Stores migrations in a structured format in the `migrations` directory
   - Tracks applied migrations in a dedicated `aerich` table
   - Uses Python files for migrations, allowing for complex migration logic
   - Supports both automatic schema detection and manual migration writing

2. **Migration Workflow**
   - **Generation**: `aerich migrate --name migration_name` creates new migration files based on model changes
   - **Application**: `aerich upgrade` applies pending migrations to the database
   - **Rollback**: `aerich downgrade -v version` allows rolling back to a previous version if needed
   - **History**: `aerich history` shows migration history
   - **Pending**: `aerich heads` shows pending migrations that haven't been applied

3. **CI/CD Integration**
   - Automatic migration application as part of the deployment process
   - Migration scripts for both Unix-based systems and Windows
   - Fail-safe checks to ensure database is properly migrated before application starts
   - Environment-specific migration handling for development, testing, and production

4. **Testing Support**
   - Uses in-memory SQLite for automated testing
   - Provides fixture utilities to set up clean test environments
   - Direct schema generation for tests without requiring migrations
   - Simulates environment variables needed for testing
   - Prevents test isolation issues with automatic cleanup

5. **Configuration**
   - Aerich configuration in `pyproject.toml` for project-wide settings
   - Tortoise ORM configuration in `src/config.py` providing database details
   - Ensures smooth integration with existing Tortoise ORM setup
   - Maintains backward compatibility with existing code

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
   - Deployed as a web service on a PaaS platform (Railway or Render)
   - Uses an ASGI server (uvicorn) for optimal async performance
   - Configured with 2 workers to handle concurrent requests efficiently
   - Direct connection between uvicorn and the aiohttp application for reduced latency
   - Handles both Telegram and payment gateway webhooks efficiently
   - Optimized for the asynchronous nature of aiogram 3.x

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
   - Application starts using uvicorn with src.main:app as the entry point
   - Multiple workers (2) for improved concurrency and reliability
   - Webhook automatically configured on application startup

4. **Railway Deployment**
   - Configured using `railway.json` for Railway-specific settings
   - Uses `Procfile` for process management
   - Configured with auto-restart on failure
   - Simple one-command deployment using Railway CLI
   - Supports both automatic and manual deployments
   - Direct integration with PostgreSQL database service on Railway
   - Automatic HTTPS handling for webhook security

5. **Monitoring & Maintenance**
   - Logging configured for production environment
   - Error handling for webhook processing
   - Graceful shutdown procedures to maintain database integrity
   - Railway dashboard for monitoring application health

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
   - Configured "Asia/Almaty" timezone (UTC+5) as the base timezone for the application
   - All timestamps are stored and processed in this timezone
   - Ensures meal pickup times are correctly displayed and filtered

2. **Timezone Utility Functions**
   - `get_current_almaty_time()`: Returns the current time in Almaty timezone
   - `to_almaty_time(dt)`: Converts any datetime to Almaty timezone
   - `ensure_timezone_aware(dt)`: Makes naive datetimes timezone-aware
   - `format_pickup_time(dt)`: Formats datetimes for display with proper timezone conversion

3. **Cross-Midnight Pickup Windows**
   - System correctly handles pickup windows that cross midnight
   - Automatically detects if end time is earlier than start time and adds a day

4. **Consistent Timezone Comparison**
   - All datetime comparisons explicitly convert both sides to Almaty timezone before comparison
   - Meal expiration checks use timezone-aware comparisons to avoid false expirations
   - Each comparison is logged with timezone information for easier debugging
   - Time comparison methodology is consistent across all features:
     - Browse meals view
     - Nearby meals search
     - Meal detail view
     - Order management

5. **Explicit Timezone Conversion**
   - Every datetime value is explicitly converted to Almaty timezone before display or comparison
   - Prevents inconsistencies between stored times and displayed/filtered times
   - Functions chain `ensure_timezone_aware()` and `to_almaty_time()` to guarantee correctness
   - Comprehensive logging tracks timezone information throughout the application

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

## Security Architecture

The application implements comprehensive security measures to protect against common threats:

1. **Rate Limiting System**
   - **User-Based Rate Limiting**
     - Configurable limits for different command types:
       - General commands (browse, view) limited to 5 requests per minute
       - Registration commands limited to 2 attempts per minute
       - Meal creation limited to 5 attempts per minute
       - Payment operations limited to 3 attempts per minute
     - Prevents command spamming and brute force attempts
     - Implemented as function decorators for easy application to handlers
     - Custom error messages inform users about rate limits
     - Tracking of frequent offenders for temporary banning

   - **IP-Based Rate Limiting (Webhook)**
     - Prevents DDOS attacks through webhook endpoints
     - Blocks IPs sending more than 30 requests in 10 seconds
     - Protects both Telegram and payment webhook endpoints
     - Background task periodically cleans up tracking data

2. **Anti-Spam Filtering**
   - Message content analysis to detect spam patterns:
     - Excessive URL detection
     - Message length limitations
     - Repetitive pattern detection
   - Blocks spam messages from being processed
   - Prevents spam propagation through the bot
   - Configurable thresholds for different spam indicators

3. **CORS Security**
   - Configures Cross-Origin Resource Sharing (CORS) policies
   - Restricts allowed HTTP methods to POST for webhook endpoints
   - Sets appropriate headers for secure cross-origin requests
   - Prevents cross-site request forgery attacks

4. **SSL Implementation**
   - Optional SSL encryption for webhook endpoints
   - Configurable through environment variables:
     - `USE_SSL`: Enable/disable SSL
     - `SSL_CERT_PATH`: Path to SSL certificate file
     - `SSL_KEY_PATH`: Path to SSL private key file
   - Ensures secure communication with webhook endpoints
   - Protects sensitive data in transit
   - Configurable for different deployment environments

5. **Memory Management**
   - Periodic cleanup of security data to prevent memory leaks:
     - Hourly cleanup of rate limiting tracking data
     - Daily reset of command usage counters
     - Automatic clearing of expired IP tracking data
   - Background task runs asynchronously without affecting main application flow
   - Efficient data structures minimize memory footprint
   - Ensures sustainable long-term operation

6. **Security Middleware**
   - AIOHTTP middleware intercepts all incoming requests:
     - Checks for rate limiting violations
     - Analyzes request properties for suspicious patterns
     - Validates content length to prevent oversized payloads
   - Integrates with the webhook handler pipeline
   - Rejects suspicious requests before significant processing
   - Logs security events for analysis and monitoring

7. **Telegram API Security**
   - Leverages Telegram Bot API's built-in security features:
     - Token-based authentication
     - Secure webhook communication
     - Protection against impersonation
   - Implements additional validation of incoming updates
   - Verifies message sources and authenticity
   - Utilizes Telegram's rate limiting mechanisms

8. **Payment Security**
   - Webhook signature verification for payment notifications
   - Validates authenticity of payment confirmation messages
   - Secure handling of payment credentials
   - Protection against replay attacks
   - Environment variable storage of sensitive payment gateway parameters

9. **Logging & Monitoring**
   - Enhanced logging for security events:
     - Rate limit violations
     - Suspected DDOS attempts
     - Spam detection
     - Authentication failures
   - Real-time monitoring of suspicious activities
   - Alerts for potential security threats
   - Detailed tracking for security investigation

10. **Configuration Management**
    - Security parameters stored as environment variables
    - Configurable rate limits for different operation types
    - Adjustable thresholds for security measures
    - Easy adaptation to different threat levels
    - Separation of development and production security settings

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
   - Timezone-aware date handling for accurate period-based reporting

5. **Dashboard for Administrators**
   - Admin-only `/metrics` command provides real-time access to key metrics
   - Overview section shows high-level performance indicators
   - Weekly conversion rates to identify funnel bottlenecks
   - Aggregated statistics on users, vendors, meals, and orders
   - Gross Merchandise Value (GMV) calculation
   - Consistent definition of "active meals" that matches the browse view (is_active=True, quantity>0, pickup_end_time in the future)
   - Proper timezone handling ensures metrics are calculated for the correct time periods

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

8. **Timezone Considerations**
   - All date calculations in metrics use the Almaty timezone (UTC+6)
   - Date ranges are properly timezone-aware to ensure accurate reporting
   - Dashboard data is generated using timezone-consistent queries
   - Metrics filtering ensures all timestamps are compared in the same timezone
   - Time-period based analysis accounts for timezone differences

9. **Future Extensions**
   The metrics system is designed for extensibility:
   - Additional metric types can be easily added
   - The reporting system can accommodate new analysis requirements
   - The underlying database schema supports detailed drill-down analysis
   - The framework supports future visualization integrations

## Webhook Testing Architecture

The application includes a comprehensive webhook testing infrastructure for development and quality assurance:

1. **Development Webhook Server**
   - Custom development script (`webhook_dev.py`) for running the bot in webhook mode locally
   - Supports both Telegram and payment webhook testing in a development environment
   - Properly configures the application to use webhook mode without code changes
   - Uses the same web application as production for consistency
   - Allows for rapid iteration and testing of webhook handlers

2. **Payment Webhook Testing Tools**
   - Dedicated script (`test_payment_webhook.py`) for simulating payment gateway webhooks
   - Supports testing various payment statuses (completed, pending, failed)
   - Properly formats webhook payloads to match production patterns
   - Includes error handling and verbose logging for debugging
   - Command-line interface with customizable parameters
   - Enables testing of the full payment flow without an actual payment provider

3. **Ngrok Integration**
   - Detailed documentation for using ngrok with the bot for webhook testing
   - Provides secure HTTPS endpoints for Telegram and payment webhook reception
   - Enables inspection of all incoming webhook requests
   - Supports testing on actual Telegram clients without deployment
   - Ensures a consistent testing environment that closely mirrors production

4. **Webhook Debugging Tools**
   - Comprehensive logging for webhook processing events
   - Proper error handling for webhook processing failures
   - Support for signature verification in webhook payloads
   - Detailed documentation for troubleshooting webhook issues
   - Step-by-step guides for webhook testing procedures

5. **Type-Safe Data Processing**
   - Robust data type validation for webhook payloads
   - Enhanced datetime handling to support both string and object inputs
   - Graceful error handling for malformed webhook data
   - Clear error messages for debugging webhook processing issues

This webhook testing infrastructure ensures that all webhook-related functionality can be thoroughly tested in a development environment before deployment, reducing the risk of issues in production.
