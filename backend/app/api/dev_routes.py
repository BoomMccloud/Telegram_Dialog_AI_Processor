"""
Development-only API routes that override standard routes with mock data.
These routes will only work when the APP_ENV is set to 'development'.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import os
import logging
import uuid
from pathlib import Path

from app.api.dependencies import get_mock_dialogs, get_mock_messages
from app.models.dialog import Dialog, Message
from app.services.auth import get_or_load_session, client_sessions

# Setup logging
logger = logging.getLogger(__name__)

# Only create the router if we're in development mode
router = APIRouter()

@router.get("/api/dialogs/{session_id}")
async def dev_list_dialogs(session_id: str):
    """
    Development-only route that overrides the standard API with mock data.
    Returns a list of mock dialogs without requiring a real Telegram client.
    """
    # Get session from memory or file storage
    session = get_or_load_session(session_id)
    
    # In development mode, we just need to verify the session exists
    # We don't need to verify if the client is authorized
    if not session:
        logger.warning(f"Invalid or expired session: {session_id}")
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    # Get mock dialogs
    mock_dialogs = get_mock_dialogs()
    
    # Return the mock dialogs
    return {"dialogs": mock_dialogs}

@router.get("/api/messages/{session_id}")
async def dev_list_messages(
    session_id: str,
    limit: Optional[int] = Query(20, description="Maximum number of messages to return"),
    offset: Optional[int] = Query(0, description="Number of messages to skip"),
    dialog_id: Optional[str] = Query(None, description="Filter messages by dialog ID")
):
    """
    Development-only route that overrides the standard API with mock data.
    Returns a list of mock messages without requiring a real Telegram client.
    """
    # Get session from memory or file storage
    session = get_or_load_session(session_id)
    
    # In development mode, we just need to verify the session exists
    # We don't need to verify if the client is authorized
    if not session:
        logger.warning(f"Invalid or expired session: {session_id}")
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    # Get mock messages
    mock_messages = get_mock_messages()
    
    # Filter by dialog_id if provided
    if dialog_id:
        mock_messages = [msg for msg in mock_messages if msg["dialog_id"] == dialog_id]
    
    # Apply pagination
    paginated_messages = mock_messages[offset:offset + limit]
    
    # Return the mock messages
    return {
        "messages": paginated_messages,
        "total": len(mock_messages),
        "limit": limit,
        "offset": offset
    }

# Add more development routes as needed

# Route for checking session status
@router.get("/api/auth/session/{session_id}")
async def dev_check_session(session_id: str):
    """
    Development-only route that checks the session status.
    """
    # Get session from memory or file storage
    session = get_or_load_session(session_id)
    
    # In development mode, we just need to verify the session exists
    if not session:
        logger.warning(f"Invalid or expired session: {session_id}")
        return JSONResponse(
            status_code=401, 
            content={"status": "error", "message": "Invalid or expired session"}
        )
    
    # Return the actual session status
    return {
        "status": session.get("status", "pending"),  # Default to pending if no status
        "user_id": session.get("user_id", 12345678),  # Use session user_id or default
        "expires_at": session.get("expires_at", (datetime.utcnow() + timedelta(hours=24))).isoformat()
    }

@router.post("/api/dialogs/{session_id}/select")
async def dev_select_dialog(
    session_id: str,
    dialog: dict = Body(...)
):
    """
    Development-only route for selecting a dialog for processing.
    This adds the dialog to the user's selected dialogs in the database,
    allowing testing of database persistence without a real Telegram client.
    """
    # Get session from memory or file storage
    session = get_or_load_session(session_id)
    
    # In development mode, we just need to verify the session exists
    if not session:
        logger.warning(f"Invalid or expired session: {session_id}")
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    # Get user_id from session
    user_id = session.get("user_id", 12345678)  # Default to mock user ID in dev mode
    
    # Validate required fields
    if "dialog_id" not in dialog:
        raise HTTPException(
            status_code=400,
            detail="dialog_id is required"
        )
    
    if "dialog_name" not in dialog:
        raise HTTPException(
            status_code=400,
            detail="dialog_name is required"
        )
    
    # Get the dialog data with defaults
    dialog_id = dialog.get("dialog_id")
    dialog_name = dialog.get("dialog_name")
    processing_enabled = dialog.get("processing_enabled", True)
    auto_reply_enabled = dialog.get("auto_reply_enabled", False)
    response_approval_required = dialog.get("response_approval_required", True)
    priority = dialog.get("priority", 0)
    processing_settings = dialog.get("processing_settings", {})
    
    # Generate a UUID for the selection
    selection_id = str(uuid.uuid4())
    
    # Get database connection
    from app.db.database import get_raw_connection
    conn = await get_raw_connection()
    
    try:
        # Check if dialog selection already exists
        existing_selection = await conn.fetchrow(
            """
            SELECT selection_id 
            FROM user_selected_dialogs
            WHERE user_id = $1 AND dialog_id = $2
            """,
            user_id, dialog_id
        )
        
        if existing_selection:
            # Update existing selection
            await conn.execute(
                """
                UPDATE user_selected_dialogs
                SET dialog_name = $1,
                    is_active = true,
                    processing_enabled = $2,
                    auto_reply_enabled = $3,
                    response_approval_required = $4,
                    priority = $5,
                    updated_at = $6,
                    processing_settings = $7
                WHERE user_id = $8 AND dialog_id = $9
                """,
                dialog_name, 
                processing_enabled,
                auto_reply_enabled,
                response_approval_required,
                priority,
                datetime.utcnow(),
                json.dumps(processing_settings),
                user_id,
                dialog_id
            )
            
            # Get the updated record
            result = await conn.fetchrow(
                """
                SELECT * FROM user_selected_dialogs
                WHERE user_id = $1 AND dialog_id = $2
                """,
                user_id, dialog_id
            )
        else:
            # Insert new selection
            result = await conn.fetchrow(
                """
                INSERT INTO user_selected_dialogs (
                    selection_id,
                    user_id,
                    dialog_id,
                    dialog_name,
                    is_active,
                    processing_enabled,
                    auto_reply_enabled,
                    response_approval_required,
                    priority,
                    created_at,
                    updated_at,
                    processing_settings
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING *
                """,
                selection_id,
                user_id,
                dialog_id,
                dialog_name,
                True,  # is_active
                processing_enabled,
                auto_reply_enabled,
                response_approval_required,
                priority,
                datetime.utcnow(),
                datetime.utcnow(),
                json.dumps(processing_settings)
            )
        
        # Convert the record to a dictionary
        record = dict(result)
        
        # Convert datetime objects to ISO format strings
        for key, value in record.items():
            if isinstance(value, datetime):
                record[key] = value.isoformat()
        
        logger.info(f"Dev route: Dialog {dialog_id} selected for user {user_id} and saved to database")
        return record
    
    except Exception as e:
        logger.error(f"Error in dev_select_dialog: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save selected dialog: {str(e)}"
        )
    finally:
        await conn.close() 

@router.get("/api/dialogs/{session_id}/selected")
async def dev_get_selected_dialogs(session_id: str):
    """
    Development-only route for getting the user's selected dialogs from the database.
    This retrieves actual data from the database, not mock data.
    """
    # Get session from memory or file storage
    session = get_or_load_session(session_id)
    
    # In development mode, we just need to verify the session exists
    if not session:
        logger.warning(f"Invalid or expired session: {session_id}")
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    # Get user_id from session
    user_id = session.get("user_id", 12345678)  # Default to mock user ID in dev mode
    
    # Get database connection
    from app.db.database import get_raw_connection
    conn = await get_raw_connection()
    
    try:
        # Fetch all selected dialogs for this user
        rows = await conn.fetch(
            """
            SELECT * FROM user_selected_dialogs
            WHERE user_id = $1 AND is_active = true
            ORDER BY priority DESC, dialog_name
            """,
            user_id
        )
        
        # Convert the records to dictionaries
        records = [dict(row) for row in rows]
        
        # Convert datetime objects to ISO format strings
        for record in records:
            for key, value in record.items():
                if isinstance(value, datetime):
                    record[key] = value.isoformat()
        
        logger.info(f"Dev route: Retrieved {len(records)} selected dialogs for user {user_id} from database")
        return records
    
    except Exception as e:
        logger.error(f"Error in dev_get_selected_dialogs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch selected dialogs: {str(e)}"
        )
    finally:
        await conn.close()

@router.delete("/api/dialogs/{session_id}/selected/{dialog_id}")
async def dev_deselect_dialog(session_id: str, dialog_id: int):
    """
    Development-only route for removing a dialog from the user's selected dialogs.
    This updates the database record to mark the dialog as inactive.
    """
    # Get session from memory or file storage
    session = get_or_load_session(session_id)
    
    # In development mode, we just need to verify the session exists
    if not session:
        logger.warning(f"Invalid or expired session: {session_id}")
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    # Get user_id from session
    user_id = session.get("user_id", 12345678)  # Default to mock user ID in dev mode
    
    # Get database connection
    from app.db.database import get_raw_connection
    conn = await get_raw_connection()
    
    try:
        # Mark dialog as inactive
        result = await conn.execute(
            """
            UPDATE user_selected_dialogs
            SET is_active = false,
                updated_at = $1
            WHERE user_id = $2 AND dialog_id = $3
            """,
            datetime.utcnow(),
            user_id,
            dialog_id
        )
        
        if result == "UPDATE 0":
            raise HTTPException(
                status_code=404,
                detail=f"Dialog {dialog_id} not found in selected dialogs"
            )
        
        logger.info(f"Dev route: Dialog {dialog_id} removed from selection for user {user_id}")
        return {"status": "success", "message": "Dialog removed from selection"}
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error in dev_deselect_dialog: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove selected dialog: {str(e)}"
        )
    finally:
        await conn.close() 

@router.post("/api/dialogs/{session_id}/process")
async def dev_process_dialogs(
    session_id: str,
    request_data: dict = Body(...)
):
    """
    Development-only route for processing selected dialogs.
    This simulates the processing endpoint without actually processing any data.
    """
    # Get session from memory or file storage
    session = get_or_load_session(session_id)
    
    # In development mode, we just need to verify the session exists
    if not session:
        logger.warning(f"Invalid or expired session: {session_id}")
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    # Validate request data
    if "dialog_ids" not in request_data or not isinstance(request_data["dialog_ids"], list):
        raise HTTPException(
            status_code=400,
            detail="dialog_ids must be provided as a non-empty array"
        )
    
    dialog_ids = request_data["dialog_ids"]
    
    if not dialog_ids:
        raise HTTPException(
            status_code=400,
            detail="dialog_ids must not be empty"
        )
    
    # Get user_id from session
    user_id = session.get("user_id", 12345678)  # Default to mock user ID in dev mode
    
    # For development, we'll just log and return success
    dialog_count = len(dialog_ids)
    logger.info(f"Dev route: Received request to process {dialog_count} dialogs for user {user_id}")
    
    return {
        "status": "success",
        "message": f"Queued {dialog_count} dialogs for processing",
        "processed_dialog_ids": dialog_ids
    } 