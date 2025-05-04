@echo off
echo Running database migrations...

REM Initialize Aerich if it's not already initialized
if not exist "migrations" (
    echo Initializing Aerich...
    aerich init -t src.config.TORTOISE_ORM
)

REM Check if the models migration location exists, if not initialize the database
if not exist "migrations\models" (
    echo Creating initial migration...
    aerich init-db
)

REM Generate migrations for any schema changes
echo Generating migrations for schema changes...
aerich migrate --name update

REM Apply all pending migrations
echo Applying pending migrations...
aerich upgrade

echo Database migrations completed successfully! 