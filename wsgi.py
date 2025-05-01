"""
WSGI entry point for Gunicorn to use in production.
"""

# Import the app from src.main
from src.main import main

# Set a global variable for Gunicorn to access
application = main

# Run main if executed directly
if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 