from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "consumers" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "telegram_id" BIGINT NOT NULL UNIQUE,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "consumers" IS 'Consumer model representing users who purchase meals.';
CREATE TABLE IF NOT EXISTS "metrics" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "metric_type" VARCHAR(19) NOT NULL,
    "value" DOUBLE PRECISION NOT NULL DEFAULT 1,
    "entity_id" INT,
    "user_id" BIGINT,
    "metadata" JSONB,
    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "metrics"."metric_type" IS 'USER_REGISTRATION: user_registration\nVENDOR_REGISTRATION: vendor_registration\nVENDOR_APPROVAL: vendor_approval\nMEAL_CREATION: meal_creation\nMEAL_VIEW: meal_view\nMEAL_BROWSE: meal_browse\nNEARBY_SEARCH: nearby_search\nORDER_CREATED: order_created\nORDER_PAID: order_paid\nORDER_COMPLETED: order_completed\nORDER_CANCELLED: order_cancelled\nPORTION_SELECTION: portion_selection';
COMMENT ON TABLE "metrics" IS 'Metrics model for tracking key performance indicators.';
CREATE TABLE IF NOT EXISTS "vendors" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "telegram_id" BIGINT NOT NULL UNIQUE,
    "name" VARCHAR(255) NOT NULL,
    "contact_phone" VARCHAR(20),
    "status" VARCHAR(8) NOT NULL DEFAULT 'pending',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "vendors"."status" IS 'PENDING: pending\nAPPROVED: approved\nREJECTED: rejected';
COMMENT ON TABLE "vendors" IS 'Vendor model representing food businesses.';
CREATE TABLE IF NOT EXISTS "meals" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT NOT NULL,
    "price" DECIMAL(10,2) NOT NULL,
    "quantity" INT NOT NULL DEFAULT 1,
    "pickup_start_time" TIMESTAMPTZ NOT NULL,
    "pickup_end_time" TIMESTAMPTZ NOT NULL,
    "location_address" TEXT NOT NULL,
    "location_latitude" DOUBLE PRECISION,
    "location_longitude" DOUBLE PRECISION,
    "is_active" BOOL NOT NULL DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "vendor_id" INT NOT NULL REFERENCES "vendors" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "meals" IS 'Meal model representing food items listed by vendors.';
CREATE TABLE IF NOT EXISTS "orders" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "status" VARCHAR(9) NOT NULL DEFAULT 'pending',
    "payment_id" VARCHAR(255),
    "quantity" INT NOT NULL DEFAULT 1,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completed_at" TIMESTAMPTZ,
    "consumer_id" INT NOT NULL REFERENCES "consumers" ("id") ON DELETE CASCADE,
    "meal_id" INT NOT NULL REFERENCES "meals" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "orders"."status" IS 'PENDING: pending\nPAID: paid\nCOMPLETED: completed\nCANCELLED: cancelled';
COMMENT ON TABLE "orders" IS 'Order model representing purchases made by consumers.';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
