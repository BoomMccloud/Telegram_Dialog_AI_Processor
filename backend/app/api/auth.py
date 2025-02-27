from fastapi import APIRouter, HTTPException
from ..services.auth import create_auth_session, get_session_status
from typing import Optional

router = APIRouter()

@router.post("/auth/qr")
async def create_qr_auth():
    """Create a new QR code authentication session using Telethon"""
    try:
        session = await create_auth_session()
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/auth/session/{session_id}")
async def check_session_status(session_id: str):
    """Check the status of an authentication session"""
    status = await get_session_status(session_id)
    if not status:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return status 