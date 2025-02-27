from fastapi import APIRouter, HTTPException
from typing import List, Dict
from ..services.telegram import get_recent_messages, send_message, get_dialogs
from pydantic import BaseModel

router = APIRouter()

class MessageSend(BaseModel):
    dialog_id: int
    text: str

@router.get("/dialogs/{session_id}")
async def list_dialogs(session_id: str) -> List[Dict]:
    """Get list of dialogs (chats)"""
    try:
        dialogs = await get_dialogs(session_id)
        return dialogs
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/messages/{session_id}")
async def list_messages(session_id: str, limit: int = 20) -> List[Dict]:
    """Get recent messages from all dialogs"""
    try:
        messages = await get_recent_messages(session_id, limit)
        return messages
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/messages/{session_id}/send")
async def create_message(session_id: str, message: MessageSend) -> Dict:
    """Send a message to a specific dialog"""
    try:
        result = await send_message(session_id, message.dialog_id, message.text)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 