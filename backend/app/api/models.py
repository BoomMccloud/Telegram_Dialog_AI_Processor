from fastapi import APIRouter, HTTPException, status
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.services.auth import get_or_load_session
from app.services.model_processor import (
    get_available_models, select_model_for_user, get_user_model
)

router = APIRouter(prefix="/api/models", tags=["models"])


class ModelSelection(BaseModel):
    """Model for selecting a model"""
    model_name: str
    system_prompt: Optional[str] = None


@router.get("/available")
async def list_available_models() -> List[Dict]:
    """
    Get a list of available models
    
    Returns:
        List of available models with their details
    """
    try:
        models = await get_available_models()
        return models
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch available models: {str(e)}"
        )


@router.post("/{session_id}/select")
async def select_model(
    session_id: str,
    model_selection: ModelSelection
) -> Dict:
    """
    Select a model for the user
    
    Args:
        session_id: The session ID of the user
        model_selection: The model to select and optional system prompt
    
    Returns:
        The selected model information
    """
    # Validate session
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
    
    try:
        result = await select_model_for_user(
            user_id, 
            model_selection.model_name,
            system_prompt=model_selection.system_prompt
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to select model")
            )
        
        return {
            "user_id": user_id,
            "model_id": result.get("model_id"),
            "model_name": result.get("model_name"),
            "system_prompt": result.get("system_prompt"),
            "message": f"Model {model_selection.model_name} selected successfully"
        }
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to select model: {str(e)}"
        )


@router.get("/{session_id}/selected")
async def get_selected_model(
    session_id: str
) -> Dict:
    """
    Get the user's currently selected model
    
    Args:
        session_id: The session ID of the user
    
    Returns:
        The user's selected model information
    """
    # Validate session
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
    
    try:
        model = await get_user_model(user_id)
        return model
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch selected model: {str(e)}"
        ) 