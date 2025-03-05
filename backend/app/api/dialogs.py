from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, List, Optional
import uuid
from datetime import datetime
import json
from pydantic import BaseModel, Field

# Import database connection
from app.db.database import get_raw_connection, get_db
# Import session middleware
from app.middleware.session import verify_session_dependency, SessionData

# Create router
router = APIRouter(prefix="/api", tags=["dialogs"])

# Pydantic models for request/response
class DialogSelection(BaseModel):
    dialog_id: int
    dialog_name: str
    processing_enabled: bool = True
    auto_reply_enabled: bool = False
    response_approval_required: bool = True
    priority: int = 0
    processing_settings: Dict = Field(default_factory=dict)

class DialogSelectionResponse(BaseModel):
    selection_id: str
    user_id: int
    dialog_id: int
    dialog_name: str
    is_active: bool
    processing_enabled: bool
    auto_reply_enabled: bool
    response_approval_required: bool
    priority: int
    created_at: str
    updated_at: str
    processing_settings: Dict

@router.post("/dialogs/select", response_model=DialogSelectionResponse)
async def select_dialog(
    dialog: DialogSelection,
    session: SessionData = Depends(verify_session_dependency),
) -> Dict:
    """
    Add a dialog to the user's selected dialogs list
    
    Args:
        dialog: Dialog selection information
    
    Returns:
        The created dialog selection record
        
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
            user_id, dialog.dialog_id
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
                dialog.dialog_name, 
                dialog.processing_enabled,
                dialog.auto_reply_enabled,
                dialog.response_approval_required,
                dialog.priority,
                datetime.utcnow(),
                json.dumps(dialog.processing_settings),
                user_id,
                dialog.dialog_id
            )
            
            # Get the updated record
            result = await conn.fetchrow(
                """
                SELECT * FROM user_selected_dialogs
                WHERE user_id = $1 AND dialog_id = $2
                """,
                user_id, dialog.dialog_id
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
                dialog.dialog_id,
                dialog.dialog_name,
                True,  # is_active
                dialog.processing_enabled,
                dialog.auto_reply_enabled,
                dialog.response_approval_required,
                dialog.priority,
                datetime.utcnow(),
                datetime.utcnow(),
                json.dumps(dialog.processing_settings)
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

@router.get("/dialogs/selected", response_model=List[DialogSelectionResponse])
async def get_selected_dialogs(
    session: SessionData = Depends(verify_session_dependency),
) -> List[Dict]:
    """
    Get the user's selected dialogs list
    
    Returns:
        List of selected dialog records
        
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

@router.delete("/dialogs/selected/{dialog_id}", response_model=DialogSelectionResponse)
async def deselect_dialog(
    dialog_id: int,
    session: SessionData = Depends(verify_session_dependency),
) -> Dict:
    """
    Remove a dialog from the user's selected dialogs list
    
    Args:
        dialog_id: The Telegram dialog ID
    
    Returns:
        The deactivated dialog selection record
        
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
        # Update the dialog selection to inactive
        result = await conn.fetchrow(
            """
            UPDATE user_selected_dialogs
            SET is_active = false,
                updated_at = $1
            WHERE user_id = $2 AND dialog_id = $3
            RETURNING *
            """,
            datetime.utcnow(),
            user_id,
            dialog_id
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected dialog not found"
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