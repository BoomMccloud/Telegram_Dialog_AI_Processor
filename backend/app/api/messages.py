from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
from ..services.telegram import get_recent_messages, send_message, get_dialogs
from pydantic import BaseModel
from ..middleware.session import verify_session_dependency, SessionData

router = APIRouter(prefix="/api", tags=["messages"])

# Request Models
class MessageSend(BaseModel):
    dialog_id: int
    text: str

# Response Models
class Dialog(BaseModel):
    id: int
    name: str
    type: str
    unread_count: Optional[int] = 0
    last_message: Optional[Dict] = None

class DialogListResponse(BaseModel):
    dialogs: List[Dialog]

class Message(BaseModel):
    id: int
    dialog_id: int
    text: str
    sender_id: Optional[int]
    sender_name: Optional[str]
    date: str

class MessageResponse(BaseModel):
    message_id: int
    dialog_id: int
    status: str = "sent"

@router.get("/dialogs", response_model=DialogListResponse)
async def list_dialogs(
    session: SessionData = Depends(verify_session_dependency)
) -> DialogListResponse:
    """
    Get list of dialogs (chats)
    
    Returns:
        List of available dialogs
        
    Note:
        Requires authentication via Bearer token in Authorization header
    """
    try:
        dialogs = await get_dialogs(session.token)
        # Return dialogs wrapped in an object with a 'dialogs' key to match dev format
        return DialogListResponse(dialogs=dialogs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/messages", response_model=List[Message])
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/messages/send", response_model=MessageResponse)
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 