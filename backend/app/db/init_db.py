#!/usr/bin/env python
import asyncio
import logging
import sys

from app.db.migrations import init_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting database initialization...")
    try:
        asyncio.run(init_db())
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        sys.exit(1) 