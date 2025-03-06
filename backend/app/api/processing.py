"""
API Router for message processing

This module provides endpoints for processing messages with LLM models
and managing the processing queue.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query, Body
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, UUID4
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.session import verify_session_dependency, SessionData
from app.services.dialog_processor import DialogProcessorService
from app.services.queue_manager import add_task_to_queue, get_queue_status, clear_queue
from app.models.processing import ProcessingStatus
from app.db.database import get_session
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# ----- Pydantic Models -----

class DialogProcessingRequest(BaseModel):
    """Request model for processing dialogs"""
    dialog_ids: List[str]
    model_name: str = "claude-3-sonnet"

class ProcessingResultUpdate(BaseModel):
    """Request model for updating processing results"""
    status: str 
    custom_reply: Optional[str] = None

class QueueStatusResponse(BaseModel):
    """Response model for queue status"""
    queue_size: int
    active_tasks: int
    processing_dialogs: List[str]
    queue_items: List[str]
    active_items: List[str]
    max_concurrent_tasks: int

# ----- API Routes -----

@router.post("/dialogs/process", 
    summary="Process selected dialogs with LLM",
    response_model=Dict[str, Any]
)
async def process_dialogs(
    request: DialogProcessingRequest,
    session_data: SessionData = Depends(verify_session_dependency),
    db: AsyncSession = Depends(get_session)
):
    """
    Process selected dialogs with the specified LLM model.
    
    This endpoint queues the selected dialogs for background processing.
    """
    try:
        # Create dialog processor service
        processor = DialogProcessorService(db)
        
        # Validate dialogs exist and belong to user
        validation_result = await processor.select_dialogs_for_processing(
            request.dialog_ids, 
            request.model_name
        )
        
        if validation_result.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_result.get("message", "Invalid dialogs")
            )
        
        # Add dialogs to processing queue
        task_ids = []
        for dialog_id in request.dialog_ids:
            task_id = add_task_to_queue({
                "type": "dialog",
                "dialog_id": dialog_id,
                "model_name": request.model_name,
                "user_id": session_data.user_id,
                "status": "pending"
            })
            task_ids.append(task_id)
        
        return {
            "status": "success",
            "message": f"Queued {len(request.dialog_ids)} dialogs for processing",
            "dialog_ids": request.dialog_ids,
            "task_ids": task_ids
        }
        
    except Exception as e:
        logger.error(f"Error queueing dialogs for processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error queueing dialogs: {str(e)}"
        )

@router.get("/processing/results", 
    summary="Get processing results",
    response_model=List[Dict[str, Any]]
)
async def get_processing_results(
    dialog_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    session_data: SessionData = Depends(verify_session_dependency),
    db: AsyncSession = Depends(get_session)
):
    """
    Get processing results.
    
    Filter by dialog_id and/or status if needed.
    """
    try:
        # Create dialog processor service
        processor = DialogProcessorService(db)
        
        # Parse status enum if provided
        status_enum = None
        if status:
            try:
                status_enum = ProcessingStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status}. Valid values are: {', '.join([s.value for s in ProcessingStatus])}"
                )
        
        # Get results
        results = await processor.get_processing_results(
            dialog_id=dialog_id,
            status=status_enum,
            limit=limit
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Error getting processing results: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting processing results: {str(e)}"
        )

@router.put("/processing/results/{result_id}", 
    summary="Update processing result",
    response_model=Dict[str, Any]
)
async def update_processing_result(
    result_id: str,
    update: ProcessingResultUpdate,
    session_data: SessionData = Depends(verify_session_dependency),
    db: AsyncSession = Depends(get_session)
):
    """
    Update a processing result (approve/reject/modify).
    """
    try:
        # Validate UUID
        try:
            uuid.UUID(result_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid result ID: {result_id}"
            )
        
        # Validate status
        try:
            status_enum = ProcessingStatus(update.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {update.status}. Valid values are: {', '.join([s.value for s in ProcessingStatus])}"
            )
        
        # Create dialog processor service
        processor = DialogProcessorService(db)
        
        # Update result
        result = await processor.update_processing_result(
            result_id=result_id,
            status=status_enum,
            custom_reply=update.custom_reply
        )
        
        if result.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Error updating processing result")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating processing result: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating processing result: {str(e)}"
        )

@router.get("/processing/queue", 
    summary="Get queue status",
    response_model=QueueStatusResponse
)
async def get_processing_queue_status(
    session_data: SessionData = Depends(verify_session_dependency)
):
    """
    Get the current status of the processing queue.
    """
    try:
        status_info = get_queue_status()
        return status_info
        
    except Exception as e:
        logger.error(f"Error getting queue status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting queue status: {str(e)}"
        )

@router.post("/processing/queue/clear", 
    summary="Clear processing queue",
    response_model=Dict[str, Any]
)
async def clear_processing_queue(
    session_data: SessionData = Depends(verify_session_dependency)
):
    """
    Clear the processing queue.
    
    This will remove all pending tasks from the queue.
    Active tasks will continue to run.
    """
    try:
        result = clear_queue()
        return result
        
    except Exception as e:
        logger.error(f"Error clearing queue: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing queue: {str(e)}"
        ) 