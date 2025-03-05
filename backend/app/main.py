"""
FastAPI application entry point
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.auth import router as auth_router
from .api.dialogs import router as dialogs_router
from .api.messages import router as messages_router
from .middleware.session import SessionMiddleware
from .db import run_migrations

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Run migrations on startup
    await run_migrations()
    yield

app = FastAPI(lifespan=lifespan)

# Initialize session middleware
session_middleware = SessionMiddleware(app)

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