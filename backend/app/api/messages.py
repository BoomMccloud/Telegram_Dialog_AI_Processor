from fastapi import APIRouter, Depends, security
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from fastapi import Query

from app.db.models.schemas import MessageResponse, DialogListResponse
from app.db.models.message import Message as DBMessage
from app.middleware.session import verify_session_dependency, SessionData
from app.services.telegram import get_dialogs, get_recent_messages, send_message
from app.core.exceptions import ValidationError, TelegramError, DatabaseError
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Define MessageSend model since it's not in schemas.py
class MessageSend(BaseModel):
    """Schema for sending a message"""
    dialog_id: int
    text: str

# Define TelegramMessage model for API responses that matches the structure returned by the Telegram service
class TelegramMessage(BaseModel):
    """Schema for Telegram message data"""
    message_id: int
    text: str
    sender: Dict[str, Any]
    date: str
    is_outgoing: bool = False
    is_unread: bool = False
    dialog_id: int
    dialog_name: Optional[str] = None

# Define custom models for Telegram dialogs that match the actual returned format
class TelegramDialog(BaseModel):
    """Schema for Telegram dialog data"""
    id: int
    name: str
    unread_count: int
    is_group: bool
    is_channel: bool
    is_user: bool
    type: str

class TelegramDialogListResponse(BaseModel):
    """Response model for list of Telegram dialogs"""
    dialogs: List[TelegramDialog]

router = APIRouter()

@router.get(
    "/dialogs", 
    response_model=TelegramDialogListResponse,
    summary="Get list of dialogs",
    description="Get list of available Telegram dialogs (chats). Requires authentication.",
    responses={
        401: {"description": "Invalid or expired session"},
        403: {"description": "Not authenticated"}
    },
    openapi_extra={
        "security": [{"BearerAuth": []}]
    }
)
async def list_dialogs(
    session: SessionData = Depends(verify_session_dependency)
) -> TelegramDialogListResponse:
    """
    Get list of dialogs (chats)
    
    Returns:
        List of available dialogs
        
    Note:
        Requires authentication via Bearer token in Authorization header
    """
    try:
        dialogs = await get_dialogs(session.token)
        return TelegramDialogListResponse(dialogs=dialogs)
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"Failed to list dialogs: {str(e)}", exc_info=True)
        raise TelegramError("Failed to fetch dialogs", details={"error": str(e)})

@router.get(
    "/dialog/{dialog_id}", 
    response_model=List[TelegramMessage],
    summary="Get messages from a specific dialog",
    description="Get messages from a specific dialog with pagination. Requires authentication.",
    responses={
        401: {"description": "Invalid or expired session"},
        403: {"description": "Not authenticated"}
    },
    openapi_extra={
        "security": [{"BearerAuth": []}]
    }
)
async def list_dialog_messages(
    dialog_id: int,
    limit: int = Query(25, description="Number of messages to return", gt=0),
    session: SessionData = Depends(verify_session_dependency)
) -> List[TelegramMessage]:
    """
    Get messages from a specific dialog
    
    Args:
        dialog_id: ID of the dialog to fetch messages from
        limit: Maximum number of messages to return (default: 25, must be greater than 0)
        
    Returns:
        List of messages from the specified dialog
        
    Note:
        Requires authentication via Bearer token in Authorization header
    """
    try:
        # Pass dialog_id as an integer to get_recent_messages
        messages = await get_recent_messages(session.token, limit, dialog_id)
        
        # Validate the messages against the TelegramMessage model
        validated_messages = []
        for msg in messages:
            try:
                validated_msg = TelegramMessage(**msg)
                validated_messages.append(validated_msg)
            except Exception as e:
                logger.warning(f"Failed to validate message: {str(e)}, message: {msg}")
                
        return validated_messages
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"Failed to list messages for dialog {dialog_id}: {str(e)}", exc_info=True)
        raise TelegramError(f"Failed to fetch messages for dialog {dialog_id}", details={"error": str(e)})

@router.post(
    "/send", 
    response_model=MessageResponse,
    summary="Send a message",
    description="Send a message to a specific dialog. Requires authentication.",
    responses={
        401: {"description": "Invalid or expired session"},
        403: {"description": "Not authenticated"}
    },
    openapi_extra={
        "security": [{"BearerAuth": []}]
    }
)
async def create_message(
    message: MessageSend,
    session: SessionData = Depends(verify_session_dependency)
) -> MessageResponse:
    """
    Send a message to a specific dialog
    
    Args:
        message: Message to send containing dialog_id and text
        
    Returns:
        Message send confirmation
        
    Note:
        Requires authentication via Bearer token in Authorization header
    """
    try:
        # Ensure dialog_id is an integer
        dialog_id = message.dialog_id
        result = await send_message(session.token, dialog_id, message.text)
        return MessageResponse(**result)
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}", exc_info=True)
        raise TelegramError("Failed to send message", details={"error": str(e)}) 