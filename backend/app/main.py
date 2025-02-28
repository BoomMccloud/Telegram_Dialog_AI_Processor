from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import logging

from .api.auth import router as auth_router
from .api.messages import router as messages_router
from .api.dialogs import router as dialogs_router
from .db.migrations import check_and_migrate_database

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if we're in development mode
DEV_MODE = os.getenv("APP_ENV", "development") == "development"
if DEV_MODE:
    logger.info("Running in DEVELOPMENT mode")
    try:
        # Import development routes
        from .api.dev_routes import router as dev_router
    except ImportError:
        logger.warning("Development routes could not be imported")

app = FastAPI(title="Telegram Dialog Processor")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if DEV_MODE else [os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# IMPORTANT ORDER CHANGE: Include development routes FIRST in development mode
# This ensures they have priority over the standard routes
if DEV_MODE:
    try:
        # Add development routes with higher precedence
        app.include_router(dev_router)
        logger.info("Development routes added with priority")
    except NameError:
        logger.warning("Development routes not available")

# Include regular routers AFTER development routes
app.include_router(auth_router, prefix="/api", tags=["auth"])
app.include_router(messages_router, prefix="/api", tags=["messages"])
app.include_router(dialogs_router)

@app.get("/health")
async def health_check():
    """
    Health check endpoint that also validates the database schema
    """
    try:
        # Check if the database schema is valid
        schema_valid = await check_and_migrate_database()
        
        if not schema_valid:
            # If schema validation failed but didn't raise an exception,
            # return a warning status
            return {
                "status": "warning",
                "message": "Database schema validation failed but automatic migration was attempted"
            }
        
        # If everything is OK
        return {
            "status": "healthy",
            "database": "connected and schema valid"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        # Return a 500 error if the health check fails
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    # Use BACKEND_PORT environment variable with fallback to 8000
    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=port) 