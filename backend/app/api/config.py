"""
Configuration management endpoints for LLM providers and model settings
"""

import json
import os
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from ..utils.logging import get_logger
from ..core.exceptions import ValidationError
from ..middleware.session import verify_session_dependency, SessionData

logger = get_logger(__name__)

# Get the config directory path
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
PROVIDER_MODELS_PATH = CONFIG_DIR / "provider_models.json"
MODEL_SETTINGS_PATH = CONFIG_DIR / "model_settings.json"

router = APIRouter(tags=["config"])

class ProviderSettings(BaseModel):
    """Settings for a specific provider"""
    model: str = Field(..., description="Model identifier")
    temperature: float = Field(..., ge=0, le=1, description="Controls randomness of output")
    max_tokens: int = Field(..., gt=0, description="Maximum tokens in response")

class ModelSettings(BaseModel):
    """Complete model settings"""
    active_provider: str = Field(..., description="Currently active provider")
    providers: Dict[str, ProviderSettings] = Field(..., description="Settings for each provider")

class ProviderModel(BaseModel):
    """Model information for a provider"""
    id: str = Field(..., description="Model identifier")
    name: str = Field(..., description="Display name")
    context_length: int = Field(..., description="Maximum context length")
    description: str = Field(..., description="Model description")

class ProviderParameter(BaseModel):
    """Parameter configuration for a provider"""
    id: str = Field(..., description="Parameter identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Parameter description")
    min: float = Field(None, description="Minimum value")
    max: float = Field(None, description="Maximum value")
    default: float = Field(..., description="Default value")
    step: float = Field(None, description="Step size for numeric parameters")

class Provider(BaseModel):
    """Provider configuration"""
    name: str = Field(..., description="Provider name")
    description: str = Field(..., description="Provider description")
    models: list[ProviderModel] = Field(..., description="Available models")
    default_model: str = Field(..., description="Default model ID")
    parameters: list[ProviderParameter] = Field(..., description="Available parameters")

class ProviderResponse(BaseModel):
    """Response model for provider configuration"""
    providers: Dict[str, Provider] = Field(..., description="Available providers and their configurations")

class SettingsResponse(BaseModel):
    """Response model for model settings"""
    active_provider: str = Field(..., description="Currently active provider")
    providers: Dict[str, ProviderSettings] = Field(..., description="Settings for each provider")

def load_provider_models() -> Dict[str, Any]:
    """Load and parse provider_models.json"""
    try:
        with open(PROVIDER_MODELS_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading provider_models.json: {e}")
        raise HTTPException(status_code=500, detail="Failed to load provider configuration")

def load_model_settings() -> Dict[str, Any]:
    """Load and parse model_settings.json"""
    try:
        with open(MODEL_SETTINGS_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading model_settings.json: {e}")
        raise HTTPException(status_code=500, detail="Failed to load model settings")

def validate_settings(settings: ModelSettings, provider_models: Dict[str, Any]) -> None:
    """Validate settings against provider_models.json"""
    providers = provider_models.get("providers", {})
    
    # Validate active provider exists
    if settings.active_provider not in providers:
        raise ValidationError(f"Invalid active_provider: {settings.active_provider}")
    
    # Validate each provider's settings
    for provider_name, provider_settings in settings.providers.items():
        if provider_name not in providers:
            raise ValidationError(f"Invalid provider: {provider_name}")
            
        provider_config = providers[provider_name]
        
        # Validate model exists for provider
        valid_models = [m["id"] for m in provider_config.get("models", [])]
        if provider_settings.model not in valid_models:
            raise ValidationError(f"Invalid model '{provider_settings.model}' for provider '{provider_name}'")
            
        # Validate parameters are within allowed ranges
        for param in provider_config.get("parameters", []):
            if param["id"] == "temperature":
                if not (param["min"] <= provider_settings.temperature <= param["max"]):
                    raise ValidationError(
                        f"Temperature {provider_settings.temperature} out of range "
                        f"[{param['min']}, {param['max']}] for provider '{provider_name}'"
                    )
            elif param["id"] == "max_tokens":
                if not (param["min"] <= provider_settings.max_tokens <= param["max"]):
                    raise ValidationError(
                        f"Max tokens {provider_settings.max_tokens} out of range "
                        f"[{param['min']}, {param['max']}] for provider '{provider_name}'"
                    )

def save_model_settings(settings: Dict[str, Any]) -> None:
    """Save settings to model_settings.json"""
    try:
        with open(MODEL_SETTINGS_PATH, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving model_settings.json: {e}")
        raise HTTPException(status_code=500, detail="Failed to save model settings")

def generate_default_settings(provider_models: Dict[str, Any]) -> Dict[str, Any]:
    """Generate default settings based on provider_models.json"""
    providers = provider_models.get("providers", {})
    settings = {
        "active_provider": next(iter(providers)),  # First provider as default
        "providers": {}
    }
    
    for provider_name, provider_config in providers.items():
        # Get default model
        default_model = provider_config.get("default_model")
        if not default_model:
            default_model = provider_config["models"][0]["id"]
            
        # Get default parameters
        default_temperature = 0.7
        default_max_tokens = 1000
        for param in provider_config.get("parameters", []):
            if param["id"] == "temperature":
                default_temperature = param["default"]
            elif param["id"] == "max_tokens":
                default_max_tokens = param["default"]
                
        settings["providers"][provider_name] = {
            "model": default_model,
            "temperature": default_temperature,
            "max_tokens": default_max_tokens
        }
    
    return settings

@router.get(
    "/providers",
    response_model=ProviderResponse,
    summary="Get available LLM providers",
    description="Get list of available LLM providers and their configurations. Requires authentication.",
    responses={
        401: {"description": "Invalid or expired session"},
        403: {"description": "Not authenticated"},
        500: {"description": "Failed to load provider configuration"}
    },
    openapi_extra={
        "security": [{"BearerAuth": []}]
    }
)
async def get_providers(
    session: SessionData = Depends(verify_session_dependency)
) -> ProviderResponse:
    """
    Get all available providers and their models
    
    Returns:
        List of available providers with their models and configurations
        
    Note:
        Requires authentication via Bearer token in Authorization header
    """
    try:
        return ProviderResponse(**load_provider_models())
    except Exception as e:
        logger.error(f"Error in get_providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/settings",
    response_model=SettingsResponse,
    summary="Get current model settings",
    description="Get current model settings for all providers. Requires authentication.",
    responses={
        401: {"description": "Invalid or expired session"},
        403: {"description": "Not authenticated"},
        500: {"description": "Failed to load model settings"}
    },
    openapi_extra={
        "security": [{"BearerAuth": []}]
    }
)
async def get_model_settings(
    session: SessionData = Depends(verify_session_dependency)
) -> SettingsResponse:
    """
    Get current model settings
    
    Returns:
        Current model settings for all providers
        
    Note:
        Requires authentication via Bearer token in Authorization header
    """
    try:
        return SettingsResponse(**load_model_settings())
    except Exception as e:
        logger.error(f"Error in get_model_settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch(
    "/settings",
    response_model=SettingsResponse,
    summary="Update model settings",
    description="Update model settings for providers. Requires authentication.",
    responses={
        400: {"description": "Invalid settings provided"},
        401: {"description": "Invalid or expired session"},
        403: {"description": "Not authenticated"},
        500: {"description": "Failed to save model settings"}
    },
    openapi_extra={
        "security": [{"BearerAuth": []}]
    }
)
async def update_model_settings(
    settings: ModelSettings,
    session: SessionData = Depends(verify_session_dependency)
) -> SettingsResponse:
    """
    Update model settings
    
    Args:
        settings: New model settings to apply
        
    Returns:
        Updated model settings
        
    Note:
        Requires authentication via Bearer token in Authorization header
    """
    try:
        # Load provider models for validation
        provider_models = load_provider_models()
        
        # Validate settings
        validate_settings(settings, provider_models)
        
        # Convert to dict and save
        settings_dict = settings.model_dump()
        save_model_settings(settings_dict)
        
        return SettingsResponse(**settings_dict)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in update_model_settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/settings/reset",
    response_model=SettingsResponse,
    summary="Reset model settings",
    description="Reset model settings to defaults for all providers. Requires authentication.",
    responses={
        401: {"description": "Invalid or expired session"},
        403: {"description": "Not authenticated"},
        500: {"description": "Failed to reset model settings"}
    },
    openapi_extra={
        "security": [{"BearerAuth": []}]
    }
)
async def reset_model_settings(
    session: SessionData = Depends(verify_session_dependency)
) -> SettingsResponse:
    """
    Reset model settings to defaults
    
    Returns:
        Default model settings
        
    Note:
        Requires authentication via Bearer token in Authorization header
    """
    try:
        # Load provider models
        provider_models = load_provider_models()
        
        # Generate and save default settings
        default_settings = generate_default_settings(provider_models)
        save_model_settings(default_settings)
        
        return SettingsResponse(**default_settings)
    except Exception as e:
        logger.error(f"Error in reset_model_settings: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 