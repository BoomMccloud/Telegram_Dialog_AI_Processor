"""
API Router for managing message processing

This module provides endpoints for processing messages with Claude and
managing the message processing queue.
"""

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from app.services.auth import get_or_load_session
from app.middleware.session_middleware import verify_session
from app.services.queue_manager import (
    enqueue_dialog_processing,
    get_processing_status,
)

router = APIRouter(prefix="/api/processing", tags=["processing"])


class ProcessingRequest(BaseModel):
    """Request to process messages in a dialog"""
    dialog_id: int
    priority: Optional[int] = 0


@router.post("/{session_id}/dialog", dependencies=[Depends(verify_session)])
async def process_dialog(
    session_id: str,
    request: ProcessingRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Process messages in a dialog with Claude
    
    Args:
        session_id: User's session ID
        request: Processing request with dialog ID
        background_tasks: FastAPI background tasks
        
    Returns:
        Status of the processing request
    """
    session = get_or_load_session(session_id)
    user_id = session.get("user_id")
    
    try:
        # Add to processing queue
        result = await enqueue_dialog_processing(
            request.dialog_id, user_id, session_id
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to enqueue dialog for processing")
            )
        
        return {
            "success": True,
            "message": f"Dialog {request.dialog_id} queued for processing",
            "queue_details": result
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error queueing dialog for processing: {str(e)}"
        )


@router.get("/{session_id}/status", dependencies=[Depends(verify_session)])
async def get_queue_status(
    session_id: str,
    dialog_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get the status of the processing queue
    
    Args:
        session_id: User's session ID
        dialog_id: Optional dialog ID to filter
        
    Returns:
        Status of the processing queue
    """
    session = get_or_load_session(session_id)
    user_id = session.get("user_id")
    
    try:
        # Get queue status
        status_info = await get_processing_status(dialog_id, user_id)
        
        return {
            "success": True,
            "status": status_info
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting queue status: {str(e)}"
        ) 