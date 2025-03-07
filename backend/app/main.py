"""
FastAPI application entry point
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing import List
import time
from sqlalchemy.sql import text

from .api import auth, messages, dialogs
from .utils.logging import get_logger
from .db.database import get_db, DATABASE_URL
from .db.models.base import Base
from .db.init_db import init_db
from .services.background_tasks import BackgroundTaskManager
from .services.cleanup import run_periodic_cleanup
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
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}", exc_info=True)
            raise DatabaseError("Failed to create database tables", details={"error": str(e)})
            
        # Start periodic cleanup task
        cleanup_interval = int(os.getenv("CLEANUP_INTERVAL_SECONDS", "3600"))
        app.state.background_tasks.add_task(
            run_periodic_cleanup(app.state.db_pool, cleanup_interval)
        )
        logger.info(f"Started periodic cleanup task with interval {cleanup_interval} seconds")
        
        # Initialize session middleware
        session_middleware = SessionMiddleware(app)
        
        # Store instances in app state
        app.state.session_middleware = session_middleware
        
        yield
        
        # Clean up background tasks
        await app.state.background_tasks.cleanup()
        
        # Clean up database
        await engine.dispose()
        logger.info("Shutting down FastAPI application...")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to initialize application", details={"error": str(e)})

app = FastAPI(title="Telegram Dialog AI Processor", lifespan=lifespan)

# Configure CORS with secure defaults
allowed_origins = get_allowed_origins()
logger.info(f"Configuring CORS with allowed origins: {allowed_origins}")

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

# Add session middleware
app.add_middleware(SessionMiddleware)

# Register error handlers
app.add_exception_handler(ValidationError, validation_error_handler)
app.add_exception_handler(TelegramError, telegram_error_handler)
app.add_exception_handler(DatabaseError, database_error_handler)
app.add_exception_handler(TelethonError, telethon_error_handler)

# Register routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(messages.router, prefix="/api/messages", tags=["messages"])
app.include_router(dialogs.router, prefix="/api/dialogs", tags=["dialogs"])

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise

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