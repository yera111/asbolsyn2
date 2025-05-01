#!/usr/bin/env python
"""
Development runner for the As Bolsyn bot.
Uses polling mode for local development.
"""
import asyncio
import os
import logging

# Make sure WEBHOOK_MODE is False for development
os.environ["WEBHOOK_MODE"] = "False"

from src.main import main

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!") 