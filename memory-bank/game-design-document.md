# Product Requirements Document: As Bolsyn - Telegram Bot (MVP)

## 1. Introduction & Goal

**Project:** As Bolsyn (meaning "enjoy your meal" in Kazakh [cite: 8]) Telegram Bot.
**Concept:** A service connecting food businesses with consumers via a Telegram bot to sell specific leftover meals at a discounted price, addressing food waste and food insecurity[cite: 1, 2, 3]. This is *not* a "surprise box" model; users will know the specific dish they are purchasing.
**MVP Goal:** Launch a functional Telegram bot in Almaty [cite: 28] with core features enabling vendors to list specific leftover meals and consumers to purchase them. Validate the core concept and gather user feedback for future iterations.

## 2. Target Audience

* **Consumers:** Students, low-income families, and everyday workers in Almaty seeking affordable, ready-to-eat meals[cite: 28].
* **Vendors:** Restaurants, cafes, and other food businesses in Almaty looking to reduce food waste and generate revenue from unsold, specific food items[cite: 3, 10, 30].

## 3. MVP Scope

* **Platform:** Telegram Bot only.
* **Geography:** Almaty, Kazakhstan only[cite: 28].
* **Language:** Russian only.
* **Monetization:** Simple commission taken from each successful transaction[cite: 11, 25].
* **Core Functionality:** Focus on listing, Browse, and purchasing specific meals[cite: 6, 19, 20].

## 4. Functional Requirements

### 4.1 Consumer User Requirements

* **Browse Meals:** Users can view a list of available meals from registered vendors within Almaty.
* **View Meal Details:** Users can see details for each listing: meal description, discounted price, quantity available, vendor name/location, and pickup time window.
* **Purchase Meal:** Users can select a meal and proceed to purchase it through the bot (requires payment integration).
* **Order Confirmation:** Users receive a confirmation message with order details and pickup instructions upon successful purchase.
* **Basic Bot Interaction:** Standard Telegram commands (/start, /help).

### 4.2 Vendor User Requirements

* **Registration/Authentication:** Vendors can securely register and log into a vendor-specific interface within the bot.
* **List Meal:** Vendors can create listings for specific leftover meals, including name, description, original price (optional), discounted price, quantity available, and pickup time window/location[cite: 6].
* **Manage Listings:** Vendors can view, edit (e.g., update quantity), or remove their active listings.
* **Order Notification:** Vendors receive notifications when a user purchases one of their listed meals.
* **Order Management (Basic):** Ability to view fulfilled/pending orders for basic tracking.

## 5. Non-Functional Requirements

* **Usability:** The bot interface must be simple, intuitive, and easy to use, even for users who aren't highly tech-savvy[cite: 24].
* **Reliability:** The bot must be available and responsive, especially during peak end-of-day hours when listings are likely posted/purchased.
* **Performance:** The bot should handle concurrent users Browse and making purchases without significant delays.
* **Security:** User data (if any collected beyond Telegram ID) and transaction details must be handled securely. Payment integration must be secure.
* **Localization:** All bot interface text must be in Russian.

## 6. Success Metrics (MVP)

These metrics will help indicate the initial success and viability of the MVP:

* **User Acquisition (Consumers):** Number of unique users interacting with the bot / starting the purchase flow.
* **User Acquisition (Vendors):** Number of registered and approved vendors actively listing meals.
* **Engagement (Listings):** Average number of meals listed per vendor per week.
* **Engagement (Sales):** Total number of meals sold via the bot per week/month.
* **Conversion Rate:** Percentage of listed meals that are successfully sold.
* **Revenue:** Total Gross Merchandise Volume (GMV) transacted through the bot and total commission earned[cite: 11, 25].
* **User Satisfaction (Qualitative):** Feedback gathered from early users (both consumers and vendors) via simple polls or direct messages.
* **Vendor Retention:** Percentage of vendors who continue listing meals after the first month.