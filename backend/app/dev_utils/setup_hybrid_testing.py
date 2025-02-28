#!/usr/bin/env python3
"""
Set up a hybrid testing environment for the Telegram Dialog Processor.

This script:
1. Injects a mock session into the main app
2. Generates and saves mock dialog data
3. Provides instructions for testing with real database endpoints

Usage:
  python -m app.dev_utils.setup_hybrid_testing

After running this script, you can:
1. Use the mock session ID with the real API endpoints
2. Test dialog selection with the real database
3. Use the mock dialog endpoints for listing dialogs
"""

import sys
import asyncio
import os
from pathlib import Path

# Add the parent directory to Python path if needed
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

# Import the session injector
from app.dev_utils.inject_mock_session import inject_mock_session
# Import the mock data generator
from app.dev_utils.mock_data_generator import save_mock_data

async def setup_hybrid_testing():
    """Set up the hybrid testing environment"""
    print("\n=== Setting up Hybrid Testing Environment ===\n")
    
    # Generate mock data
    print("Generating mock dialog data...")
    save_mock_data()
    
    # Inject mock session
    print("\nInjecting mock session...")
    session_id = await inject_mock_session()
    
    # Print instructions
    print("\n=== Hybrid Testing Ready ===\n")
    print("You can now test the real database endpoints with mock authentication.")
    print("\nExample requests:")
    print(f"1. Get mock dialogs (uses mock data):")
    print(f"   GET http://localhost:8000/api/dialogs/{session_id}")
    print(f"\n2. Select a dialog (uses real database):")
    print(f"   POST http://localhost:8000/api/dialogs/{session_id}/select")
    print(f"   Body: {{\"dialog_id\": -10000000, \"dialog_name\": \"Laura\"}}")
    print(f"\n3. List selected dialogs (uses real database):")
    print(f"   GET http://localhost:8000/api/dialogs/{session_id}/selected")
    print(f"\n4. Deselect a dialog (uses real database):")
    print(f"   DELETE http://localhost:8000/api/dialogs/{session_id}/selected/-10000000")
    
    print("\nThe session ID is saved to 'app/dev_utils/mock_session.txt' for reference.")
    print("\nHappy testing!\n")

if __name__ == "__main__":
    # Run the async function
    asyncio.run(setup_hybrid_testing()) 