from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, List, Optional
import uuid
from datetime import datetime
import json
from pydantic import BaseModel, Field, validator
import re

# Import database connection
from app.db.database import get_raw_connection, get_db
# Import session middleware
from app.middleware.session import verify_session_dependency, SessionData

# Create router
router = APIRouter()

# Pydantic models for request/response
class DialogSelection(BaseModel):
    dialog_id: str
    dialog_name: str
    is_processing_enabled: bool = True
    auto_send_enabled: bool = False
    priority: int = 0

    @validator('dialog_id')
    def validate_dialog_id(cls, v):
        # Validate Telegram chat ID format
        # Private chats: positive numbers
        # Groups: -number
        # Supergroups/Channels: -100number
        if not re.match(r'^-?(?:100)?\d+$', v):
            raise ValueError('Invalid Telegram chat ID format')
        return v

    @validator('priority')
    def validate_priority(cls, v):
        if v < 0:
            raise ValueError('Priority must be non-negative')
        return v

class DialogSelectionResponse(BaseModel):
    selection_id: str
    dialog_id: str
    dialog_name: str
    is_active: bool
    is_processing_enabled: bool
    auto_send_enabled: bool
    priority: int
    created_at: str
    updated_at: str

    @validator('dialog_id')
    def validate_dialog_id(cls, v):
        if not re.match(r'^-?(?:100)?\d+$', v):
            raise ValueError('Invalid Telegram chat ID format')
        return v

    @validator('priority')
    def validate_priority(cls, v):
        if v < 0:
            raise ValueError('Priority must be non-negative')
        return v

@router.post("/dialogs/select", 
    response_model=DialogSelectionResponse,
    summary="Enable processing for a dialog",
    description="Enable AI processing for a specific dialog. Requires authentication.",
    responses={
        401: {"description": "Invalid or expired session"},
        403: {"description": "Not authenticated"}
    },
    openapi_extra={
        "security": [{"BearerAuth": []}]
    }
)
async def select_dialog(
    dialog: DialogSelection,
    session: SessionData = Depends(verify_session_dependency),
) -> Dict:
    """
    Enable processing for a dialog
    
    Args:
        dialog: Dialog selection information
    
    Returns:
        The updated dialog record
        
    Note:
        Requires authentication via Bearer token in Authorization header
    """
    # Get user_id from session
    user_id = session.telegram_id
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session user"
        )
    
    # Get db connection
    conn = await get_raw_connection()
    
    try:
        # Update the dialog's processing settings
        result = await conn.fetchrow(
            """
            UPDATE dialogs
            SET is_processing_enabled = $1,
                auto_send_enabled = $2,
                priority = $3,
                updated_at = $4
            WHERE user_id = $5 AND telegram_dialog_id = $6
            RETURNING 
                id as selection_id,
                telegram_dialog_id as dialog_id,
                name as dialog_name,
                true as is_active,
                is_processing_enabled,
                auto_send_enabled,
                priority,
                created_at,
                updated_at
            """,
            dialog.is_processing_enabled,
            dialog.auto_send_enabled,
            dialog.priority,
            datetime.utcnow(),
            user_id,
            str(dialog.dialog_id)  # Convert to string as telegram_dialog_id is VARCHAR
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dialog not found"
            )
        
        # Convert the record to a dictionary
        record = dict(result)
        
        # Convert datetime objects to ISO format strings
        for key, value in record.items():
            if isinstance(value, datetime):
                record[key] = value.isoformat()
        
        return record
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to select dialog: {str(e)}"
        )
    finally:
        await conn.close()

@router.get("/dialogs/selected", 
    response_model=List[DialogSelectionResponse],
    summary="Get selected dialogs",
    description="Get all dialogs with processing enabled. Requires authentication.",
    responses={
        401: {"description": "Invalid or expired session"},
        403: {"description": "Not authenticated"}
    },
    openapi_extra={
        "security": [{"BearerAuth": []}]
    }
)
async def get_selected_dialogs(
    session: SessionData = Depends(verify_session_dependency),
) -> List[Dict]:
    """
    Get the user's selected dialogs list (dialogs with processing enabled)
    
    Returns:
        List of selected dialog records
        
    Note:
        Requires authentication via Bearer token in Authorization header
    """
    # Get db connection
    conn = await get_raw_connection()
    
    try:
        # Fetch all selected dialogs (where processing is enabled)
        rows = await conn.fetch(
            """
            SELECT 
                id as selection_id,
                telegram_dialog_id as dialog_id,
                name as dialog_name,
                true as is_active,
                is_processing_enabled,
                auto_send_enabled,
                priority,
                created_at,
                updated_at
            FROM dialogs
            WHERE user_id = (
                SELECT id FROM users WHERE telegram_id = $1
            )
            AND is_processing_enabled = true
            ORDER BY priority DESC, name
            """,
            session.telegram_id
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

@router.delete("/dialogs/selected/{dialog_id}", 
    response_model=DialogSelectionResponse,
    summary="Disable processing for a dialog",
    description="Disable AI processing for a specific dialog. Requires authentication.",
    responses={
        401: {"description": "Invalid or expired session"},
        403: {"description": "Not authenticated"}
    },
    openapi_extra={
        "security": [{"BearerAuth": []}]
    }
)
async def deselect_dialog(
    dialog_id: str,
    session: SessionData = Depends(verify_session_dependency),
) -> Dict:
    """
    Disable processing for a dialog
    
    Args:
        dialog_id: The Telegram dialog ID (as a string)
    
    Returns:
        The updated dialog record
        
    Note:
        Requires authentication via Bearer token in Authorization header
    """
    # Get user_id from session
    user_id = session.telegram_id
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session user"
        )
    
    # Get db connection
    conn = await get_raw_connection()
    
    try:
        # Update the dialog to disable processing
        result = await conn.fetchrow(
            """
            UPDATE dialogs
            SET is_processing_enabled = false,
                auto_send_enabled = false,
                priority = 0,
                updated_at = $1
            WHERE user_id = $2 AND telegram_dialog_id = $3
            RETURNING 
                id as selection_id,
                telegram_dialog_id as dialog_id,
                name as dialog_name,
                false as is_active,
                is_processing_enabled,
                auto_send_enabled,
                priority,
                created_at,
                updated_at
            """,
            datetime.utcnow(),
            user_id,
            str(dialog_id)  # Convert to string as telegram_dialog_id is VARCHAR
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dialog not found"
            )
        
        # Convert the record to a dictionary
        record = dict(result)
        
        # Convert datetime objects to ISO format strings
        for key, value in record.items():
            if isinstance(value, datetime):
                record[key] = value.isoformat()
        
        return record
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deselect dialog: {str(e)}"
        )
    finally:
        await conn.close() 