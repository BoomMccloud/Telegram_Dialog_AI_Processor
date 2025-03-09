from fastapi import APIRouter, Depends, security
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime

from app.db.models.schemas import MessageResponse, DialogListResponse
from app.db.models.message import Message
from app.middleware.session import verify_session_dependency, SessionData
from app.services.telegram import get_dialogs, get_recent_messages, send_message
from app.core.exceptions import ValidationError, TelegramError, DatabaseError
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Define MessageSend model since it's not in schemas.py
class MessageSend(BaseModel):
    """Schema for sending a message"""
    dialog_id: str
    text: str

# Define Message model for API responses
class Message(BaseModel):
    """Schema for message data"""
    id: Optional[str] = None
    text: str
    sender_id: str
    sender_name: str
    date: datetime
    is_outgoing: bool = False
    dialog_id: Optional[str] = None

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
    "/messages", 
    response_model=List[Message],
    summary="Get recent messages",
    description="Get recent messages from all dialogs. Requires authentication.",
    responses={
        401: {"description": "Invalid or expired session"},
        403: {"description": "Not authenticated"}
    },
    openapi_extra={
        "security": [{"BearerAuth": []}]
    }
)
async def list_messages(
    limit: int = 20,
    session: SessionData = Depends(verify_session_dependency)
) -> List[Message]:
    """
    Get recent messages from all dialogs
    
    Args:
        limit: Maximum number of messages to return (default: 20)
        
    Returns:
        List of recent messages
        
    Note:
        Requires authentication via Bearer token in Authorization header
    """
    try:
        messages = await get_recent_messages(session.token, limit)
        return messages
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"Failed to list messages: {str(e)}", exc_info=True)
        raise TelegramError("Failed to fetch messages", details={"error": str(e)})

@router.post(
    "/messages/send", 
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
        result = await send_message(session.token, message.dialog_id, message.text)
        return MessageResponse(**result)
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}", exc_info=True)
        raise TelegramError("Failed to send message", details={"error": str(e)}) 