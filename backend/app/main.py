from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import logging
import asyncio
from contextlib import asynccontextmanager

from .api.auth import router as auth_router
from .api.messages import router as messages_router
from .api.dialogs import router as dialogs_router
from .db.migrations import check_and_migrate_database, init_db
from .db.migrate_model_data import migrate_model_data
from .api import auth, dialogs, messages, models

# Import session functions
from .services.auth import load_all_sessions, cleanup_sessions, periodic_cleanup, ensure_sessions_dir

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

# Configure CORS origins
allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

# Background task for periodic cleanup
cleanup_task = None

async def start_periodic_cleanup():
    """Start periodic cleanup of stale sessions"""
    while True:
        try:
            # Run cleanup every 30 minutes
            await asyncio.sleep(30 * 60)  # 30 minutes
            await periodic_cleanup()
        except asyncio.CancelledError:
            logger.info("Periodic cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {str(e)}")
            # Wait a bit before retrying
            await asyncio.sleep(60)

# Define lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events"""
    global cleanup_task
    
    current_env = os.getenv("APP_ENV", "development")
    print(f"Starting application in {current_env} environment")
    
    # Create sessions directory if it doesn't exist
    ensure_sessions_dir()
    
    # Load existing sessions at startup
    loaded_count = load_all_sessions()
    print(f"Loaded {loaded_count} sessions at startup")
    
    # Start periodic cleanup
    cleanup_task = asyncio.create_task(start_periodic_cleanup())
    print("Started periodic session cleanup task")
    
    # Startup: initialize database
    try:
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialization complete.")
        
        # Run model data migration
        logger.info("Running model data migration...")
        await migrate_model_data()
        logger.info("Model data migration complete.")
        
        # Run an initial cleanup to remove any stale sessions
        cleanup_count = await periodic_cleanup()
        logger.info(f"Initial cleanup complete: removed {cleanup_count} stale sessions")
        
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
    
    yield
    
    # Cancel the periodic cleanup task
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    
    # Cleanup at shutdown
    await cleanup_sessions()
    print("Application shutdown complete")

app = FastAPI(
    title="Telegram Dialog AI Processor",
    description="API for processing Telegram messages with AI",
    version="0.1.0",
    lifespan=lifespan
)

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