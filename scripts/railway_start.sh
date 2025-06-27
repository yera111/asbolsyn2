#!/bin/bash
set -e

echo "Railway startup script starting..."

# Wait for database to be ready
echo "Waiting for database to be ready..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    echo "Checking database connection (attempt $((attempt + 1))/$max_attempts)..."
    
    # Try to connect to the database using python
    if python3 -c "
import asyncio
import sys
import os
sys.path.append('.')
from src.config import DB_URL
from tortoise import Tortoise

async def test_connection():
    try:
        await Tortoise.init(db_url='$DB_URL', modules={'models': ['src.models']})
        await Tortoise.close_connections()
        return True
    except Exception as e:
        print(f'Connection failed: {e}')
        return False

result = asyncio.run(test_connection())
sys.exit(0 if result else 1)
"; then
        echo "Database is ready!"
        break
    else
        echo "Database not ready, waiting 2 seconds..."
        sleep 2
        attempt=$((attempt + 1))
    fi
done

if [ $attempt -eq $max_attempts ]; then
    echo "Database connection failed after $max_attempts attempts"
    exit 1
fi

echo "Starting application..."
exec python -m src.main 