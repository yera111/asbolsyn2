-- Manual migration script to add earnings tracking tables
-- Run this script in your PostgreSQL database

-- Create commissions table
CREATE TABLE IF NOT EXISTS "commissions" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "commission_rate" DECIMAL(5,4) NOT NULL DEFAULT 0.15,
    "effective_from" TIMESTAMPTZ NOT NULL,
    "effective_to" TIMESTAMPTZ,
    "description" VARCHAR(255),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create vendor_earnings table
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

-- Create payout_requests table
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

-- Add comments
COMMENT ON TABLE "commissions" IS 'Platform commission rates over time';
COMMENT ON TABLE "vendor_earnings" IS 'Vendor earnings tracking per order';
COMMENT ON TABLE "payout_requests" IS 'Monthly payout requests for vendors';

-- Initialize default commission rate
INSERT INTO "commissions" ("commission_rate", "effective_from", "description") 
VALUES (0.15, CURRENT_TIMESTAMP, 'Default platform commission rate (15%)')
ON CONFLICT DO NOTHING;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Earnings tracking tables created successfully!';
    RAISE NOTICE 'Tables: commissions, vendor_earnings, payout_requests';
    RAISE NOTICE 'Default commission rate (15%%) initialized';
END $$; 