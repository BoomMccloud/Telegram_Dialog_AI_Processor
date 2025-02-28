from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, List, Optional
import uuid
from datetime import datetime
import json

# Import database connection
from app.db.database import get_raw_connection
# Import auth validation from services
from app.services.auth import get_or_load_session

# Create router
router = APIRouter(prefix="/api", tags=["dialogs"])

@router.post("/dialogs/{session_id}/select")
async def select_dialog(
    session_id: str,
    dialog: Dict,
) -> Dict:
    """
    Add a dialog to the user's selected dialogs list
    
    Args:
        session_id: The user's session ID
        dialog: A dictionary containing dialog information with at least:
            - dialog_id (int): The Telegram dialog ID
            - dialog_name (str): The name of the dialog
            - processing_enabled (bool, optional): Whether processing is enabled
            - auto_reply_enabled (bool, optional): Whether auto-reply is enabled
            - response_approval_required (bool, optional): Whether response approval is required
            - priority (int, optional): Processing priority
            - processing_settings (Dict, optional): Additional processing settings
    
    Returns:
        The created dialog selection record
    """
    # Validate the session
    session = get_or_load_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    # Get user_id from session
    user_id = session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session user"
        )
    
    # Validate required fields
    if "dialog_id" not in dialog:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dialog_id is required"
        )
    
    if "dialog_name" not in dialog:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dialog_name is required"
        )
    
    # Get defaults or provided values
    dialog_id = dialog["dialog_id"]
    dialog_name = dialog["dialog_name"]
    processing_enabled = dialog.get("processing_enabled", True)
    auto_reply_enabled = dialog.get("auto_reply_enabled", False)
    response_approval_required = dialog.get("response_approval_required", True)
    priority = dialog.get("priority", 0)
    processing_settings = dialog.get("processing_settings", {})
    
    # Generate a UUID for the selection
    selection_id = str(uuid.uuid4())
    
    # Get db connection
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
        
        return record
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save selected dialog: {str(e)}"
        )
    finally:
        await conn.close()

@router.get("/dialogs/{session_id}/selected")
async def get_selected_dialogs(
    session_id: str,
) -> List[Dict]:
    """
    Get the user's selected dialogs list
    
    Args:
        session_id: The user's session ID
    
    Returns:
        List of selected dialog records
    """
    # Validate the session
    session = get_or_load_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    # Get user_id from session
    user_id = session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session user"
        )
    
    # Get db connection
    conn = await get_raw_connection()
    
    try:
        # Fetch all selected dialogs
        rows = await conn.fetch(
            """
            SELECT * FROM user_selected_dialogs
            WHERE user_id = $1
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
        
        return records
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch selected dialogs: {str(e)}"
        )
    finally:
        await conn.close()

@router.delete("/dialogs/{session_id}/selected/{dialog_id}")
async def deselect_dialog(
    session_id: str,
    dialog_id: int,
) -> Dict:
    """
    Remove a dialog from the user's selected dialogs list
    
    Args:
        session_id: The user's session ID
        dialog_id: The Telegram dialog ID
    
    Returns:
        Status message
    """
    # Validate the session
    session = get_or_load_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    # Get user_id from session
    user_id = session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session user"
        )
    
    # Get db connection
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
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dialog {dialog_id} not found in selected dialogs"
            )
        
        return {"status": "success", "message": "Dialog removed from selection"}
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove selected dialog: {str(e)}"
        )
    finally:
        await conn.close() 