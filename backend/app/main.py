"""
FastAPI application entry point
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .api.auth import router as auth_router
from .api.dialogs import router as dialogs_router
from .api.messages import router as messages_router
from .utils.logging import get_logger
from .db.database import get_db, DATABASE_URL
from .db.base import Base
from .services.background_tasks import BackgroundTaskManager
from .services.cleanup import run_periodic_cleanup
from .middleware.session import SessionMiddleware

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
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Add session middleware
app.add_middleware(SessionMiddleware)

# Include routers
app.include_router(auth_router)
app.include_router(dialogs_router)
app.include_router(messages_router)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"} 