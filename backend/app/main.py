"""
Main FastAPI application module
"""

import os
from contextlib import asynccontextmanager
import asyncio
from typing import AsyncGenerator
import logging

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .api.auth import router as auth_router
from .api.messages import router as messages_router
from .api.dialogs import router as dialogs_router
from .api.models import router as models_router
from .api.responses import router as responses_router
from .db.migrations import check_and_migrate_database, init_db
from .db.migrate_model_data import migrate_model_data
from .middleware.session import SessionMiddleware
from .services.auth import init_session_middleware

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
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

# Configure CORS origins
allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

# Session cleanup interval in seconds
SESSION_CLEANUP_INTERVAL = int(os.getenv("SESSION_CLEANUP_INTERVAL", "300"))  # 5 minutes default

async def cleanup_sessions_task(app: FastAPI):
    """Background task to clean up expired sessions"""
    while True:
        try:
            await app.state.session_middleware.cleanup_expired_sessions()
        except Exception as e:
            logger.error(f"Error in session cleanup task: {str(e)}")
        await asyncio.sleep(SESSION_CLEANUP_INTERVAL)

# Define lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events"""
    current_env = os.getenv("APP_ENV", "development")
    print(f"Starting application in {current_env} environment")
    
    # Start session cleanup task
    cleanup_task = asyncio.create_task(cleanup_sessions_task(app))
    print("Started session cleanup task")
    
    # Startup: initialize database
    try:
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialization complete.")
        
        # Run model data migration
        logger.info("Running model data migration...")
        await migrate_model_data()
        logger.info("Model data migration complete.")
        
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
    
    yield
    
    # Cancel cleanup task on shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    
    print("Application shutdown complete")

app = FastAPI(
    title="Telegram Dialog AI Processor",
    description="API for processing Telegram messages with AI",
    version="0.1.0",
    lifespan=lifespan
)

# Initialize session middleware and share it with auth service
session_middleware = SessionMiddleware(app)
init_session_middleware(session_middleware)  # Share with auth service
app.add_middleware(SessionMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
app.include_router(models_router)
app.include_router(responses_router)

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

@app.on_event("startup")
async def startup_event():
    """Initialize any resources needed on startup"""
    logger.info("Starting up FastAPI application")
    # Additional startup tasks can be added here

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    logger.info("Shutting down FastAPI application")
    # Additional cleanup tasks can be added here

if __name__ == "__main__":
    import uvicorn
    # Use BACKEND_PORT environment variable with fallback to 8000
    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=port) 