#!/usr/bin/env python
"""
Development runner for the As Bolsyn bot with webhook support.
For use with ngrok for local webhook testing.
"""
import os
import logging
import sys

# Force webhook mode for development testing
os.environ["WEBHOOK_MODE"] = "True"

# Import here after setting environment variables
from src.main import app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Starting bot in WEBHOOK mode for development testing...")
    
    # Import and use aiohttp's run_app directly to avoid event loop issues
    from aiohttp import web
    
    try:
        # Don't start a new event loop - let web.run_app handle it
        web.run_app(app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        logging.info("Bot stopped by user!")
    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1) 