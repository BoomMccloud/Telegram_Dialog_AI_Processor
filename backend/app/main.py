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
from .middleware.session import SessionMiddleware
from .db.database import get_db, DATABASE_URL
from .db.base import Base
from .utils.logging import get_logger

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
    
    # Initialize session middleware
    app.state.session_middleware = SessionMiddleware(app)
    
    # Create database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}", exc_info=True)
        raise
    
    yield
    
    # Clean up
    await engine.dispose()
    logger.info("Shutting down FastAPI application...")

app = FastAPI(lifespan=lifespan)

# Add session middleware to the app
@app.middleware("http")
async def session_middleware_handler(request, call_next):
    path = request.url.path
    logger.debug(f"Processing request to {path}")
    return await app.state.session_middleware(request, call_next)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(auth_router)
app.include_router(dialogs_router)
app.include_router(messages_router)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"} 