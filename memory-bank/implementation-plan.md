# Implementation Plan: As Bolsyn - Telegram Bot MVP

**Goal:** Create the Minimum Viable Product (MVP) for the As Bolsyn Telegram bot according to the [Product Requirements Document](game-design-document.md) and [Technology Stack Proposal](tech-stack.md). This plan focuses on core functionality for launch in Almaty, Kazakhstan, with Russian language support only.

**Technology Stack:**
* **Language/Framework:** Python 3 / `aiogram`
* **Database:** PostgreSQL with Tortoise ORM
* **Hosting:** PaaS (e.g., Render)
* **Payment:** Kazakhstan-Specific Provider (Research needed, assume integration via API)

**Guiding Principles:**
* Follow instructions in `C:\Users\111\Desktop\app5\.cursor\rules\customrules.mdc`.
* Steps must be small and specific.
* Each step requires a validation test.
* All user-facing text must be in Russian (provided text strings should be used, not machine translation).
* Update architecture.md after completing major features or milestones.
* Track progress in progress.md.

---

## Phase 1: Project Setup & Basic Bot Structure

**Step 1.1: Initialize Project & Environment**
* **Instruction:** Set up the Python project structure using `aiogram`. Initialize a Git repository. Configure environment variables for the Telegram Bot Token and database credentials. Set up dependency management (e.g., `requirements.txt` or `pyproject.toml` with Poetry). Ensure all sensitive data is stored securely using environment variables, not hardcoded in the repository.
* **Test:** Run the basic `aiogram` bot template locally. Verify it connects to Telegram using the token by sending `/start` to the bot and receiving a default welcome message.

**Step 1.2: Database Schema Setup (Core Models)**
* **Instruction:** Define and create the initial PostgreSQL database schema using Tortoise ORM for its asyncio integration with aiogram. Include tables for `Vendors` (with status field for approval tracking), `Consumers` (linking to Telegram User IDs), `Meals` (with fields for name, description, price, quantity, pickup time, vendor foreign key, location coordinates), and `Orders` (linking consumers, meals, status, payment details).
* **Test:** Connect to the PostgreSQL database from the Python environment. Verify that all specified tables and columns exist with the correct data types using Tortoise ORM introspection.

**Step 1.3: Basic Bot Commands & Russian Localization Setup**
* **Instruction:** Implement basic command handlers (`/start`, `/help`) using `aiogram`. Set up a simple localization system (e.g., using dictionaries or a dedicated library) to manage all user-facing strings. Ensure all initial bot responses are in Russian using the provided text strings.
* **Test:** Send `/start` and `/help` to the bot. Verify the responses are received, are entirely in Russian, and match the expected introductory/help text.

---

## Phase 2: Vendor Features

**Step 2.1: Vendor Registration (Admin Approval Process)**
* **Instruction:** Implement a command or conversation flow for vendors to register. Store vendor information (Telegram ID, name, contact details) in the `Vendors` table with status "pending". Automatically send a notification to a designated admin Telegram chat/user about the new registration. Create an admin command (e.g., `/approve_vendor <vendor_id>`) to update vendor status to "approved" after manual vetting. Ensure only approved vendors can list meals.
* **Test:** Use a test Telegram account, initiate the vendor registration flow. Verify the bot prompts for necessary information (in Russian), that a new record appears in the `Vendors` table with "pending" status, and that the admin notification is sent. Test the admin approval command and confirm it changes the vendor's status.

**Step 2.2: Meal Listing Creation**
* **Instruction:** Create a conversation flow (`ConversationHandler` in `aiogram`) for registered vendors to list a specific leftover meal. Prompt for: meal name, description, discounted price, quantity, pickup time window, and pickup location (address text initially). Store this information in the `Meals` table, linked to the vendor. Include input validation for all fields to prevent injection attacks.
* **Test:** As a registered test vendor, use the meal listing command. Go through the flow, providing details for a sample meal. Verify all prompts are in Russian. Check the `Meals` table to confirm the meal is saved correctly with all details and linked to the correct vendor ID. Test with invalid inputs to verify validation.

**Step 2.3: Meal Location - Storing Coordinates**
* **Instruction:** Modify the meal listing flow (Step 2.2). Add a step where the vendor shares their location using Telegram's native location sharing feature for the pickup point. Extract latitude and longitude from the shared location message and store these coordinates in the `Meals` table alongside the address text.
* **Test:** As a registered test vendor, list a new meal. When prompted for location, use Telegram to share a specific location within Almaty. Verify the bot acknowledges the location. Check the `Meals` table to confirm both the address text and the corresponding latitude/longitude are saved for the meal.

**Step 2.4: Manage Listings (View/Delete)**
* **Instruction:** Implement commands for vendors to view their active listings and to delete a specific listing. Display listings clearly with key details.
* **Test:** As a test vendor with active listings, use the 'view listings' command. Verify all active listings for that vendor are shown correctly (in Russian). Use the 'delete listing' command on one meal. Verify it's removed from the view and marked inactive/deleted in the database.

---

## Phase 3: Consumer Features

**Step 3.1: Browse Meals (Basic List)**
* **Instruction:** Implement a command for consumers to browse all currently active meal listings. Display results as a simple list showing essential details (name, price, vendor name).
* **Test:** As a consumer test account, use the 'browse meals' command. Verify a list of active meals (created by test vendors) is displayed in Russian.

**Step 3.2: Filter Meals Nearby**
* **Instruction:** Implement a "Find meals nearby" command. This command should prompt the consumer to share their current location using Telegram's location sharing. Use the consumer's coordinates and the stored coordinates for each active meal to calculate the distance (using Haversine formula or a GeoDjango/PostGIS function if available). Display only meals within a predefined radius (e.g., 3km) in Almaty, ordered by distance.
* **Test:** As a consumer test account in a simulated Almaty location, use the 'find nearby' command and share location. Verify the bot only shows meals listed within the defined radius of the shared location. Test with locations that should return results and locations that should return none. Ensure results are in Russian.

**Step 3.3: View Meal Details**
* **Instruction:** Allow consumers to select a meal from the browse/nearby list (e.g., via inline buttons) to view full details: description, discounted price, quantity, vendor name/location text, pickup time window. Include a "Buy" button.
* **Test:** Browse or find nearby meals. Select a specific meal. Verify all details are displayed correctly and in Russian. Confirm the "Buy" button is present.

---

## Phase 4: Payment & Order Flow

**Step 4.1: Payment Provider Research & Selection**
* **Instruction:** Research and select a suitable Kazakhstan-based payment provider (e.g., Kaspi Pay, PayBox.money). Evaluate based on: clear API documentation, Python SDK availability, acceptable fees, commission handling (for the platform's 15-25% fee after the 1-month free trial period), payout simplicity for vendors, and popularity/trust among Almaty consumers. Obtain API keys for a test environment.
* **Test:** Successfully make test API calls (e.g., authentication, creating a test payment link) to the chosen provider's sandbox environment using tools like `curl` or `Postman`.

**Step 4.2: Payment Integration - Create Payment**
* **Instruction:** Integrate the chosen payment provider's API. When a consumer clicks "Buy" (Step 3.3), call the payment provider's API to create a payment link or checkout session for the meal's price. Store the pending transaction details (linking user, meal, payment ID) in the `Orders` table with status 'pending'. Ensure all payment endpoints use HTTPS.
* **Test:** As a consumer, select a meal and click "Buy". Verify the bot responds with a valid payment link (in Russian) from the payment provider's test environment. Check the `Orders` table for a new record with 'pending' status.

**Step 4.3: Payment Confirmation (Webhook)**
* **Instruction:** Implement a webhook endpoint (requires the PaaS deployment) to receive payment success notifications from the payment provider. When a successful payment notification arrives, verify its authenticity, update the corresponding `Orders` record status to 'paid', and decrease the quantity of the purchased `Meal`. Implement basic rate limiting on the webhook endpoint to prevent abuse.
* **Test:** Simulate a successful payment callback from the payment provider to the webhook endpoint (using provider's sandbox tools or manual simulation). Verify the `Orders` status changes to 'paid' and the `Meals` quantity is decremented correctly. Test with invalid webhooks to ensure proper validation.

**Step 4.4: Order Confirmation & Notification**
* **Instruction:** Upon successful payment confirmation (Webhook in Step 4.3):
    * Send an order confirmation message (in Russian) to the consumer, including meal details, vendor pickup location/time, and a unique order identifier.
    * Send a notification message (in Russian) to the relevant vendor, informing them of the sale, which meal was sold, and the order identifier.
* **Test:** After simulating a successful payment (Step 4.3), verify that the consumer test account receives a correct confirmation message and the vendor test account receives a correct notification message, both in Russian.

---

## Phase 5: Deployment & Refinement

**Step 5.1: Initial Deployment to PaaS**
* **Instruction:** Configure the chosen PaaS (e.g., Render) for deployment. Set up the production database (PostgreSQL) and configure environment variables (Bot Token, DB Credentials, Payment API Keys - Production). Deploy the application. Set up the Telegram Bot Webhook to point to the deployed application URL. Ensure all endpoints use HTTPS.
* **Test:** Interact with the deployed bot on Telegram. Test the `/start` command and verify it's operational. Ensure the webhook is correctly set and receiving updates from Telegram.

**Step 5.2: End-to-End Testing**
* **Instruction:** Perform full end-to-end tests on the deployed version covering all implemented user flows: Vendor registers, lists meal with location, Consumer finds meal nearby, purchases meal (using test payment), Vendor receives notification, Consumer receives confirmation.
* **Test:** Successfully complete the entire workflow described in the instruction using separate test accounts for vendor and consumer on the live deployed bot (using test payment credentials). Verify all messages are in Russian and data is correctly updated in the production database.

---

## Priority and Execution

The phases should be executed sequentially (1 -> 2 -> 3 -> 4 -> 5), focusing on delivering the end-to-end functionality as quickly as possible to test the core product hypothesis: connecting food businesses with consumers to sell specific leftover meals at discounted prices.

Throughout implementation, remember to:
1. Update architecture.md after completing significant parts of each phase
2. Track progress in progress.md
3. Follow all security practices (secure storage of secrets, input validation, HTTPS, etc.)
4. Use provided Russian text strings for all user-facing content