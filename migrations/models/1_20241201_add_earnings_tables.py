from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "commissions" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "commission_rate" DECIMAL(5,4) NOT NULL DEFAULT 0.15,
            "effective_from" TIMESTAMPTZ NOT NULL,
            "effective_to" TIMESTAMPTZ,
            "description" VARCHAR(255),
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS "vendor_earnings" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "vendor_id" INT NOT NULL REFERENCES "vendors" ("id") ON DELETE CASCADE,
            "order_id" INT NOT NULL REFERENCES "orders" ("id") ON DELETE CASCADE,
            "gross_amount" DECIMAL(10,2) NOT NULL,
            "commission_rate" DECIMAL(5,4) NOT NULL,
            "commission_amount" DECIMAL(10,2) NOT NULL,
            "net_amount" DECIMAL(10,2) NOT NULL,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "period_year" INT NOT NULL,
            "period_month" INT NOT NULL,
            "is_paid_out" BOOL NOT NULL DEFAULT FALSE,
            "paid_out_at" TIMESTAMPTZ
        );
        
        CREATE TABLE IF NOT EXISTS "payout_requests" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "vendor_id" INT NOT NULL REFERENCES "vendors" ("id") ON DELETE CASCADE,
            "amount" DECIMAL(10,2) NOT NULL,
            "currency" VARCHAR(3) NOT NULL DEFAULT 'KZT',
            "status" VARCHAR(20) NOT NULL DEFAULT 'pending',
            "period_year" INT NOT NULL,
            "period_month" INT NOT NULL,
            "external_transaction_id" VARCHAR(255),
            "external_notes" TEXT,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "processed_at" TIMESTAMPTZ,
            "completed_at" TIMESTAMPTZ,
            UNIQUE("vendor_id", "period_year", "period_month")
        );
        
        -- Create indexes for better performance
        CREATE INDEX IF NOT EXISTS "idx_vendor_earnings_vendor_period" ON "vendor_earnings" ("vendor_id", "period_year", "period_month");
        CREATE INDEX IF NOT EXISTS "idx_vendor_earnings_paid_out" ON "vendor_earnings" ("is_paid_out");
        CREATE INDEX IF NOT EXISTS "idx_payout_requests_status" ON "payout_requests" ("status");
        
        -- Add new metric types to support earnings tracking
        -- Note: This assumes the metrics table already exists and uses enum-like constraints
        -- If using CHECK constraints for metric_type, they would need to be updated
        
        COMMENT ON TABLE "commissions" IS 'Platform commission rates over time';
        COMMENT ON TABLE "vendor_earnings" IS 'Vendor earnings tracking per order';
        COMMENT ON TABLE "payout_requests" IS 'Monthly payout requests for vendors';
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "payout_requests";
        DROP TABLE IF EXISTS "vendor_earnings";
        DROP TABLE IF EXISTS "commissions";
    """ 