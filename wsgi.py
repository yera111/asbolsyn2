"""
WSGI entry point - DEPRECATED, kept for backward compatibility.

NOTE: This project now uses ASGI with uvicorn directly accessing src.main:app.
This file is maintained for backward compatibility but is no longer used
in the production deployment, which uses:
    uvicorn src.main:app --host 0.0.0.0 --port $PORT --workers 2

For new deployments, please use the ASGI approach.
"""

# Import the app from src.main
from src.main import main

# Set a global variable for Gunicorn to access
application = main

# Run main if executed directly
if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 