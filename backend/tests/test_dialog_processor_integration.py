"""
Integration tests for the dialog processor workflow.

These tests test the complete workflow from selecting dialogs to approving processing results.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.dialog import Dialog, Message
from app.db.models.processed_response import ProcessedResponse, ProcessingStatus
from app.db.models.user import User
from app.middleware.session import create_session
from app.services.dialog_processor import DialogProcessorService
from app.api.processing import router as processing_router

# Constants
API_PREFIX = ""
TEST_MODEL = "claude-3-sonnet"

# --- Test Authentication Helpers ---

async def authenticate_test_user(client: AsyncClient, test_user: User, db: AsyncSession):
    """Create a session for the test user and authenticate."""
    # Create session for test user
    session_data = {
        "user_id": test_user.id,
        "telegram_id": test_user.telegram_id,
        "expires_at": (datetime.now() + timedelta(hours=1)).isoformat()
    }
    
    # Create session in database
    session_id, access_token = await create_session(
        db, test_user.id, session_data
    )
    
    # Set authentication header
    client.headers.update({"Authorization": f"Bearer {access_token}"})
    
    return access_token

# --- Integration Tests ---

@pytest.mark.asyncio
async def test_full_dialog_processing_workflow(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_dialogs: List[Dialog],
    test_messages: List[Message]
):
    """
    Test the complete dialog processing workflow:
    1. Authenticate user
    2. Select dialogs for processing
    3. Queue processes dialogs
    4. Retrieve processing results
    5. Approve/reject results
    """
    # Authenticate test user
    access_token = await authenticate_test_user(client, test_user, db_session)
    
    # Select the first dialog for processing
    dialog_id = str(test_dialogs[0].id)
    
    # Mock the actual dialog processor to avoid actual LLM calls
    # This would typically be done with a proper mock framework
    # For this test, we'll directly add processing results to the database
    
    # First, queue the dialog for processing
    response = await client.post(
        f"{API_PREFIX}/api/dialogs/process",
        json={
            "dialog_ids": [dialog_id],
            "model_name": TEST_MODEL
        }
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["task_ids"]) == 1
    
    # Since we can't actually run the background worker in tests,
    # directly create processing results for the messages
    for message in test_messages[:2]:  # First two messages belong to first dialog
        if not message.is_outgoing:  # Only process incoming messages
            result = ProcessingResult(
                message_id=message.id,
                model_name=TEST_MODEL,
                status=ProcessingStatus.COMPLETED,
                result={
                    "suggested_reply": "This is a test response for message: " + message.text,
                    "processed_at": datetime.now().isoformat()
                },
                completed_at=datetime.now()
            )
            
            db_session.add(result)
    
    await db_session.commit()
    
    # Get processing results
    response = await client.get(
        f"{API_PREFIX}/api/processing/results",
        params={"dialog_id": dialog_id}
    )
    
    # Verify response
    assert response.status_code == 200
    results = response.json()
    assert len(results) > 0
    
    # Get the first result
    result_id = results[0]["id"]
    
    # Approve the result
    response = await client.put(
        f"{API_PREFIX}/api/processing/results/{result_id}",
        json={
            "status": "completed",
            "custom_reply": "This is a custom reply that I've edited."
        }
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    
    # Get the updated result
    response = await client.get(
        f"{API_PREFIX}/api/processing/results",
        params={"dialog_id": dialog_id}
    )
    
    # Verify the result was updated
    results = response.json()
    updated_result = next((r for r in results if r["id"] == result_id), None)
    assert updated_result is not None
    assert updated_result["status"] == "completed"
    assert updated_result["result"]["custom_reply"] == "This is a custom reply that I've edited."
    
    # Test queue status endpoint
    response = await client.get(f"{API_PREFIX}/api/processing/queue")
    assert response.status_code == 200
    queue_status = response.json()
    assert "queue_size" in queue_status
    assert "active_tasks" in queue_status
    
    # Test clearing the queue
    response = await client.post(f"{API_PREFIX}/api/processing/queue/clear")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success" 