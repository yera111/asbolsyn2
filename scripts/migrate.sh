#!/bin/bash
set -e

echo "Running database migrations..."

# Initialize Aerich if it's not already initialized
if [ ! -d "migrations" ]; then
    echo "Initializing Aerich..."
    aerich init -t src.config.TORTOISE_ORM
fi

# Check if the models migration location exists, if not initialize the database
if [ ! -d "migrations/models" ]; then
    echo "Creating initial migration..."
    aerich init-db
fi

# Generate migrations for any schema changes
echo "Generating migrations for schema changes..."
aerich migrate --name update

# Apply all pending migrations
echo "Applying pending migrations..."
aerich upgrade

echo "Database migrations completed successfully!" 