# Technology Stack Proposal: As Bolsyn - Telegram Bot MVP

## Goal

To select the **simplest** technology stack that is also **robust** enough for an MVP launch, allowing for rapid development, easy deployment, and reliable operation for early users in Almaty.

## Proposed Stack

1.  **Backend Language & Bot Framework:**
    * **Choice:** **Python 3** with **`python-telegram-bot`** or **`aiogram`**.
    * **Rationale:**
        * *Simplicity:* Python has a gentle learning curve and clean syntax, facilitating rapid development. Both `python-telegram-bot` and `aiogram` are mature libraries with excellent documentation and community support, making Telegram API interaction straightforward. `aiogram` is particularly well-suited for asynchronous operations, common in bots.
        * *Robustness:* Python is a stable, widely-used language. The libraries are well-maintained. Asynchronous frameworks like `aiogram` handle concurrent users efficiently, crucial for a responsive bot. Vast libraries available for database interaction, payments, etc.

2.  **Database:**
    * **Choice:** **PostgreSQL**
    * **Rationale:**
        * *Simplicity:* While requiring a separate server process (unlike SQLite), managed PostgreSQL offerings on PaaS/cloud platforms make setup very easy. Standard SQL is relatively simple for the required data structures (vendors, meals, orders). Excellent, mature Python drivers (e.g., `psycopg2`).
        * *Robustness:* PostgreSQL is known for its reliability, data integrity (ACID compliance), and ability to handle concurrent transactions well. It provides a solid foundation that can scale beyond the MVP stage if needed, avoiding the limitations of simpler file-based databases.

3.  **Payment Gateway Integration:**
    * **Choice:** **Kazakhstan-Specific Provider (e.g., Kaspi Pay, Halyk EPay, PayBox.money - *Requires Research*)**
    * **Rationale:**
        * *Simplicity:* Integration complexity will vary, but choosing a provider with clear API documentation and ideally a Python SDK will be simplest.
        * *Robustness:* Requires a reliable, established payment processor legally operating and widely used within Kazakhstan to handle transactions securely and ensure user trust. The final choice depends on researching local providers' APIs, fees, terms, and ease of integration.

4.  **Hosting / Deployment:**
    * **Choice:** **Platform-as-a-Service (PaaS) - e.g., Render, Heroku, Railway**
    * **Rationale:**
        * *Simplicity:* PaaS platforms abstract away most infrastructure management (servers, operating systems, patching). Deployment is often as simple as `git push`. They usually offer easy integration with managed PostgreSQL databases and handle scaling (to a degree) automatically. Free/low-cost tiers are available for MVPs.
        * *Robustness:* These platforms are designed for hosting web applications and services, providing a reliable environment with monitoring and easy rollbacks, more robust than managing a single VPS manually at the MVP stage.

## Summary

| Component        | Choice                                                       | Why Simple?                                       | Why Robust?                                         |
| :--------------- | :----------------------------------------------------------- | :------------------------------------------------ | :-------------------------------------------------- |
| **Language** | Python 3                                                     | Easy syntax, fast development, large community    | Mature, stable, good library support                |
| **Bot Framework**| `python-telegram-bot` / `aiogram`                            | High-level abstraction, great docs/examples       | Well-maintained, handles concurrency (async)      |
| **Database** | PostgreSQL                                                   | Standard SQL, excellent Python drivers, PaaS ease | ACID compliant, reliable, scalable, handles writes well |
| **Payments** | Local KZ Provider (TBD)                                      | Choose based on API clarity & SDK availability  | Established, secure, compliant processor          |
| **Hosting** | PaaS (Render, Heroku, etc.)                                  | `git push` deployment, managed infra & DB       | Reliable environment, monitoring, easy scaling    |

This stack prioritizes developer productivity and operational simplicity for the MVP while ensuring the core components (database, language, hosting) are reliable enough for real users and provide a reasonable path for future growth.