"""
FastAPI application entry point
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .api import auth, messages
from .utils.logging import get_logger
from .db.database import get_db, DATABASE_URL
from .db.base import Base
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

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events"""
    logger.info("Starting up FastAPI application...")
    logger.info(f"Connecting to database: {DATABASE_URL}")
    
    # Create database engine
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
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
        raise
        
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

app = FastAPI(lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware
app.add_middleware(SessionMiddleware)

# Register error handlers
app.add_exception_handler(ValidationError, validation_error_handler)
app.add_exception_handler(TelegramError, telegram_error_handler)
app.add_exception_handler(DatabaseError, database_error_handler)
app.add_exception_handler(TelethonError, telethon_error_handler)

# Register routers
app.include_router(auth.router)
app.include_router(messages.router)

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
    """Health check endpoint"""
    return {"status": "healthy"} 