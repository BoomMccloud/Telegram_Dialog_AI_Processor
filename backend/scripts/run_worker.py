#!/usr/bin/env python
"""
Script to run the background worker directly.
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent.parent / "logs" / "worker.log")
    ]
)

# Import the worker
from app.services.worker import main

if __name__ == "__main__":
    try:
        # Run the worker
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Worker stopped by keyboard interrupt")
    except Exception as e:
        print(f"Error running worker: {str(e)}")
        sys.exit(1) 