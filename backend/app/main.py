"""
FastAPI application entry point
"""

import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing import List
import time
from sqlalchemy.sql import text
from fastapi.openapi.utils import get_openapi
from datetime import datetime, timezone

from .api import auth, messages, dialogs, responses
from .utils.logging import get_logger
from .db.database import get_db, DATABASE_URL
from .db.models.base import Base
from .db.init_db import init_db
from .services.background_tasks import BackgroundTaskManager
from .services.cleanup import run_periodic_cleanup
from .services.worker import DialogWorker
from .middleware.session import SessionMiddleware
from .core.exceptions import ValidationError, TelegramError, DatabaseError
from .core.error_handlers import (
    validation_error_handler,
    telegram_error_handler,
    database_error_handler,
    telethon_error_handler
)
from sqlalchemy.exc import SQLAlchemyError
from telethon.errors import RPCError as TelethonError
from .db.utils import check_database_connection

logger = get_logger(__name__)

def get_allowed_origins() -> List[str]:
    """Get list of allowed origins from environment variables"""
    # Default to localhost in development
    default_origins = [
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:8000",  # FastAPI dev server
    ]
    
    # Get additional origins from environment
    env_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    origins = [origin.strip() for origin in env_origins if origin.strip()]
    
    # In development, use default origins if none specified
    if not origins and os.getenv("ENV", "development") == "development":
        logger.warning("No CORS origins specified, using development defaults")
        return default_origins
        
    return origins

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events"""
    logger.info("Starting up FastAPI application...")
    logger.info(f"Connecting to database: {DATABASE_URL}")
    
    # Flag to signal worker to stop
    app.state.should_exit = False
    
    # Worker task reference
    worker_task = None
    
    try:
        # Create database engine with retries
        engine = create_async_engine(
            DATABASE_URL,
            pool_pre_ping=True,  # Enable connection health checks
            pool_size=5,  # Set a reasonable pool size
            max_overflow=10,  # Allow some overflow connections
            echo=True  # Log SQL queries for debugging
        )
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        # Test database connection
        try:
            async with engine.begin() as conn:
                # Test basic connectivity
                await conn.execute(text("SELECT 1"))
                logger.info("Basic database connection test successful")
                
                # Test if we can create tables
                await conn.execute(text("CREATE TABLE IF NOT EXISTS _test_connection (id serial PRIMARY KEY)"))
                await conn.execute(text("DROP TABLE _test_connection"))
                logger.info("Database write permissions test successful")
                
            logger.info("All database connection tests passed")
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}", exc_info=True)
            raise DatabaseError("Failed to connect to database", details={"error": str(e)})
            
        # Create database pool
        app.state.db_pool = async_session
        
        # Initialize background task manager
        app.state.background_tasks = BackgroundTaskManager()
        
        # Create database tables
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}", exc_info=True)
            raise DatabaseError("Failed to create database tables", details={"error": str(e)})
            
        # Initialize session middleware
        app.state.session_middleware = SessionMiddleware(app)
        
        # Start periodic cleanup task
        cleanup_coro = run_periodic_cleanup(app.state.db_pool)
        app.state.background_tasks.add_task(cleanup_coro)
        
        # Start dialog worker
        worker = DialogWorker(interval_seconds=600)  # Run every 10 minutes
        
        async def run_worker():
            """Run the worker in a background task"""
            logger.info("Starting dialog worker...")
            while not app.state.should_exit:
                try:
                    await worker.run_once()
                except Exception as e:
                    logger.error(f"Error in worker cycle: {str(e)}", exc_info=True)
                
                # Sleep until next interval
                for _ in range(int(worker.interval_seconds)):
                    if app.state.should_exit:
                        break
                    await asyncio.sleep(1)
        
        # Start worker in background task
        worker_task = asyncio.create_task(run_worker())
        logger.info("Dialog worker started")
        
        # Yield control back to FastAPI
        yield
        
        # Shutdown tasks
        logger.info("Shutting down FastAPI application...")
        
        # Signal worker to stop
        app.state.should_exit = True
        
        # Wait for worker to stop
        if worker_task:
            logger.info("Waiting for dialog worker to stop...")
            try:
                await asyncio.wait_for(worker_task, timeout=30.0)
                logger.info("Dialog worker stopped")
            except asyncio.TimeoutError:
                logger.warning("Dialog worker did not stop gracefully, cancelling...")
                worker_task.cancel()
        
        # Stop background tasks
        await app.state.background_tasks.shutdown()
        logger.info("Background tasks stopped")
        
    except Exception as e:
        logger.error(f"Error during application startup: {str(e)}", exc_info=True)
        # Clean up any tasks if startup failed
        if worker_task and not worker_task.done():
            worker_task.cancel()
        raise

app = FastAPI(
    title="Telegram Dialog AI Processor", 
    lifespan=lifespan,
    # Add OpenAPI security scheme for Bearer token
    openapi_tags=[
        {"name": "auth", "description": "Authentication operations"},
        {"name": "messages", "description": "Message operations"},
        {"name": "dialogs", "description": "Dialog operations"},
        {"name": "responses", "description": "Response operations"}
    ],
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "persistAuthorization": True  # This makes the authorization persist between page refreshes
    }
)

# Configure CORS with secure defaults
allowed_origins = get_allowed_origins()
logger.info(f"Configuring CORS with allowed origins: {allowed_origins}")

# Add the security scheme to the OpenAPI specification
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Add security scheme to OpenAPI schema
security_schemes = {
    "BearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Enter your JWT token in the format 'Bearer your_token_here'"
    }
}

# Update the app's OpenAPI info
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        description="Telegram Dialog AI Processor API",
        routes=app.routes,
    )
    
    # Add security schemes to the components
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    openapi_schema["components"]["securitySchemes"] = security_schemes
    
    # Add global security requirement
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Register global security for all routes that will appear in Swagger UI
app.swagger_ui_init_oauth = {
    "usePkceWithAuthorizationCodeGrant": True,
    "clientId": "swagger-ui",
    "scopes": ["read", "write"]
}

# Register error handlers
app.add_exception_handler(ValidationError, validation_error_handler)
app.add_exception_handler(TelegramError, telegram_error_handler)
app.add_exception_handler(DatabaseError, database_error_handler)
app.add_exception_handler(TelethonError, telethon_error_handler)

# Register routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(messages.router, prefix="/api/messages", tags=["messages"])
app.include_router(dialogs.router, prefix="/api", tags=["dialogs"])
app.include_router(responses.router, prefix="/api", tags=["responses"])

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        await init_db()
        logger.info("Database initialized successfully")
        
        # Load existing Telethon sessions
        await load_existing_sessions()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise

async def load_existing_sessions():
    """Load existing Telethon sessions into memory"""
    try:
        from app.services.auth import SESSIONS_DIR, load_telegram_client_from_session, client_sessions
        from app.db.models.user import User
        from app.db.models.session import Session, SessionStatus
        from sqlalchemy import select
        
        # Get all session files
        session_files = list(SESSIONS_DIR.glob("*.session"))
        if not session_files:
            logger.info("No Telethon session files found")
            return
            
        logger.info(f"Found {len(session_files)} Telethon session files")
        
        # Get all authenticated users
        async with app.state.db_pool() as db:
            stmt = select(User).where(User.telegram_id.is_not(None))
            result = await db.execute(stmt)
            users = result.scalars().all()
            
            if not users:
                logger.info("No authenticated users found in database")
                return
                
            logger.info(f"Found {len(users)} authenticated users in database")
            
            # Get active sessions for these users
            stmt = select(Session).where(
                Session.user_id.in_([user.id for user in users]),
                Session.status == SessionStatus.AUTHENTICATED,
                Session.expires_at > datetime.now(timezone.utc)
            )
            result = await db.execute(stmt)
            active_sessions = result.scalars().all()
            
            if not active_sessions:
                logger.info("No active sessions found in database")
                return
                
            logger.info(f"Found {len(active_sessions)} active sessions in database")
            
            # Try to load each session
            loaded_count = 0
            for session_file in session_files:
                try:
                    client = await load_telegram_client_from_session(str(session_file))
                    if client:
                        # Get the user ID from the client
                        me = await client.get_me()
                        if not me:
                            await client.disconnect()
                            continue
                            
                        # Find the user in our database
                        user = next((u for u in users if u.telegram_id == me.id), None)
                        if not user:
                            await client.disconnect()
                            continue
                            
                        # Find active sessions for this user
                        user_sessions = [s for s in active_sessions if s.user_id == user.id]
                        if not user_sessions:
                            await client.disconnect()
                            continue
                            
                        # Store the client in memory for each active session
                        for session in user_sessions:
                            client_sessions[session.token] = {
                                "client": client,
                                "status": "authenticated",
                                "telegram_id": user.telegram_id
                            }
                            loaded_count += 1
                            
                        logger.info(f"Loaded Telethon session for user {me.id} ({me.username})")
                except Exception as e:
                    logger.error(f"Error loading session file {session_file}: {str(e)}", exc_info=True)
                    
            logger.info(f"Successfully loaded {loaded_count} Telethon sessions")
    except Exception as e:
        logger.error(f"Error loading existing sessions: {str(e)}", exc_info=True)
        # Don't raise the exception to allow the application to start

@app.get("/health")
async def health_check():
    """Health check endpoint with database verification"""
    try:
        # Get database session from pool
        async with app.state.db_pool() as session:
            # Check database connection
            is_healthy, error = await check_database_connection(session)
            
            # Return appropriate status based on database health
            status = "healthy" if is_healthy else "unhealthy"
            db_status = "connected" if is_healthy else "error"
            
            response = {
                "status": status,
                "database": {
                    "status": db_status
                }
            }
            
            if is_healthy:
                response["database"]["latency"] = await get_db_latency(session)
            else:
                response["database"]["error"] = str(error)
            
            return response
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "database": {
                "status": "error",
                "error": str(e)
            }
        }

async def get_db_latency(session: AsyncSession) -> float:
    """Measure database query latency"""
    start_time = time.time()
    await session.execute(text("SELECT 1"))
    return round((time.time() - start_time) * 1000, 2)  # Convert to milliseconds 

@app.get("/")
async def root():
    return {"message": "Welcome to Telegram Dialog AI Processor"} 