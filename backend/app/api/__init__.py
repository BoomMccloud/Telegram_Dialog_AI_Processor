"""
API Router initialization and configuration.
Combines all API endpoints into a single router with proper middleware and error handling.
"""

from fastapi import APIRouter
from . import auth, dialogs, messages, responses
# TODO: Import settings module once implemented
# from . import settings

# Create main API router
api_router = APIRouter()

# Include all sub-routers with their prefixes
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    dialogs.router,
    prefix="/dialogs",
    tags=["Dialog Management"]
)

api_router.include_router(
    messages.router,
    prefix="/messages",
    tags=["Message Management"]
)

api_router.include_router(
    responses.router,
    prefix="/responses",
    tags=["Response Management"]
)

# TODO: Add settings router once implemented
# api_router.include_router(
#     settings.router,
#     prefix="/settings",
#     tags=["User Settings"]
# )

# Export the combined router
__all__ = ["api_router"] 