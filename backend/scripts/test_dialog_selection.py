#!/usr/bin/env python3
"""
Test script for dialog selection API endpoints

This script tests the dialog selection API endpoints:
- POST /api/dialogs/{session_id}/select (select a dialog)
- GET /api/dialogs/{session_id}/selected (get selected dialogs)
- DELETE /api/dialogs/{session_id}/selected/{dialog_id} (deselect a dialog)

Usage:
  python test_dialog_selection.py

The script assumes the mock API server is running on http://localhost:8001.
"""

import os
import sys
import json
import requests
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Set the base URL for the API
BASE_URL = "http://localhost:8001"

def get_session_id():
    """
    Get a session ID from the dummy_session.txt file or create a new one
    """
    try:
        # Try to read the session ID from the file
        session_file = Path(__file__).resolve().parent / "dummy_session.txt"
        if session_file.exists():
            session_id = session_file.read_text().strip()
            print(f"Using existing session ID: {session_id}")
            
            # Verify the session is valid
            response = requests.get(f"{BASE_URL}/api/auth/session/{session_id}")
            if response.status_code != 200:
                raise ValueError("Invalid session")
            
            return session_id
    except Exception as e:
        print(f"Error reading session ID: {str(e)}")
    
    # Create a new session
    print("Creating a new session...")
    response = requests.post(f"{BASE_URL}/api/auth/qr")
    if response.status_code != 200:
        raise Exception(f"Failed to create session: {response.text}")
    
    session_data = response.json()
    session_id = session_data["session_id"]
    
    # Save the session ID to a file
    session_file = Path(__file__).resolve().parent / "dummy_session.txt"
    session_file.write_text(session_id)
    
    print(f"Created new session ID: {session_id}")
    return session_id

def test_select_dialog(session_id):
    """
    Test selecting a dialog
    """
    print("\n--- Testing dialog selection ---")
    
    # First, get list of dialogs to select from
    response = requests.get(f"{BASE_URL}/api/dialogs/{session_id}")
    if response.status_code != 200:
        raise Exception(f"Failed to get dialogs: {response.text}")
    
    dialogs = response.json()
    if not dialogs:
        raise Exception("No dialogs available for testing")
    
    # Select the first dialog
    dialog = dialogs[0]
    dialog_id = dialog["id"]
    dialog_name = dialog["name"]
    
    # Create payload for selection
    payload = {
        "dialog_id": dialog_id,
        "dialog_name": dialog_name,
        "processing_enabled": True,
        "auto_reply_enabled": False,
        "response_approval_required": True,
        "priority": 5,
        "processing_settings": {
            "max_context_messages": 10,
            "response_style": "concise"
        }
    }
    
    # Select the dialog
    print(f"Selecting dialog: {dialog_name} (ID: {dialog_id})")
    response = requests.post(
        f"{BASE_URL}/api/dialogs/{session_id}/select",
        json=payload
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to select dialog: {response.text}")
    
    result = response.json()
    print(f"Successfully selected dialog: {json.dumps(result, indent=2)}")
    
    return dialog_id, dialog_name

def test_get_selected_dialogs(session_id):
    """
    Test getting selected dialogs
    """
    print("\n--- Testing get selected dialogs ---")
    
    # Get selected dialogs
    response = requests.get(f"{BASE_URL}/api/dialogs/{session_id}/selected")
    if response.status_code != 200:
        raise Exception(f"Failed to get selected dialogs: {response.text}")
    
    selected_dialogs = response.json()
    print(f"Selected dialogs ({len(selected_dialogs)}):")
    for dialog in selected_dialogs:
        print(f"  - {dialog['dialog_name']} (ID: {dialog['dialog_id']}, Priority: {dialog['priority']})")
    
    return selected_dialogs

def test_deselect_dialog(session_id, dialog_id):
    """
    Test deselecting a dialog
    """
    print(f"\n--- Testing dialog deselection for dialog ID {dialog_id} ---")
    
    # Deselect the dialog
    response = requests.delete(f"{BASE_URL}/api/dialogs/{session_id}/selected/{dialog_id}")
    if response.status_code != 200:
        raise Exception(f"Failed to deselect dialog: {response.text}")
    
    result = response.json()
    print(f"Successfully deselected dialog: {result['message']}")
    
    # Verify dialog is no longer in selected list
    selected_dialogs = test_get_selected_dialogs(session_id)
    
    # Check if the deselected dialog is still in the list
    for dialog in selected_dialogs:
        if dialog["dialog_id"] == dialog_id:
            raise Exception(f"Dialog {dialog_id} still appears in selected list after deselection")
    
    print(f"Verified dialog {dialog_id} is no longer in selected list")

def main():
    """
    Main function to run the tests
    """
    print("=== Dialog Selection API Test ===")
    print(f"API URL: {BASE_URL}")
    
    try:
        # Get a session ID
        session_id = get_session_id()
        
        # Test dialog selection
        dialog_id, dialog_name = test_select_dialog(session_id)
        
        # Test getting selected dialogs
        test_get_selected_dialogs(session_id)
        
        # Test dialog deselection
        test_deselect_dialog(session_id, dialog_id)
        
        # Select the dialog again for testing further functionality
        print("\n--- Reselecting dialog for further testing ---")
        payload = {
            "dialog_id": dialog_id,
            "dialog_name": dialog_name,
            "processing_enabled": True,
            "auto_reply_enabled": True,  # Different from before
            "response_approval_required": False,  # Different from before
            "priority": 10,  # Different from before
            "processing_settings": {
                "max_context_messages": 5,
                "response_style": "detailed"
            }
        }
        
        # Select the dialog again
        response = requests.post(
            f"{BASE_URL}/api/dialogs/{session_id}/select",
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to reselect dialog: {response.text}")
        
        result = response.json()
        print(f"Successfully reselected dialog with updated settings")
        
        # Verify the updated settings
        response = requests.get(f"{BASE_URL}/api/dialogs/{session_id}/selected")
        selected_dialogs = response.json()
        
        for dialog in selected_dialogs:
            if dialog["dialog_id"] == dialog_id:
                print("\nUpdated dialog settings:")
                print(f"  - Auto-reply enabled: {dialog['auto_reply_enabled']}")
                print(f"  - Response approval required: {dialog['response_approval_required']}")
                print(f"  - Priority: {dialog['priority']}")
                print(f"  - Processing settings: {dialog['processing_settings']}")
                break
        
        print("\n=== All tests passed successfully ===")
    
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 