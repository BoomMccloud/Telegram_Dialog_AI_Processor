from fastapi import FastAPI, Request
from httpx import AsyncClient, ASGITransport
import pytest

from app.middleware.session import SessionMiddleware

@pytest.mark.asyncio
async def test_session_middleware_basic():
    """Test basic session middleware functionality"""
    app = FastAPI()
    session_middleware = SessionMiddleware(testing=True)
    app.middleware("http")(session_middleware)
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
        
    @app.get("/api/protected")
    async def protected_route(request: Request):
        # If we get here, it means the session middleware allowed the request
        return {"message": "success"}
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test 1: Public endpoint should work without token
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        
        # Test 2: Protected endpoint should fail without token
        response = await client.get("/api/protected")
        assert response.status_code == 401
        assert response.json()["detail"] == "Authorization header required"
        
        # Test 3: Protected endpoint should work with valid token
        token = await session_middleware.create_session(telegram_id=123456)
        response = await client.get(
            "/api/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json() == {"message": "success"}

@pytest.mark.asyncio
async def test_jwt_token_creation():
    """Test JWT token creation and verification"""
    session_middleware = SessionMiddleware(testing=True)
    
    # Create a new session token
    token = await session_middleware.create_session(telegram_id=123456)
    assert token is not None
    
    # Verify the token
    session = await session_middleware.verify_session(token)
    assert session.telegram_id == 123456

@pytest.mark.asyncio
async def test_expired_token():
    """Test handling of expired tokens"""
    app = FastAPI()
    session_middleware = SessionMiddleware(testing=True)
    app.middleware("http")(session_middleware)
    
    @app.get("/api/protected")
    async def protected_route():
        return {"message": "success"}
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test with expired token - should fail with 401
        response = await client.get(
            "/api/protected",
            headers={"Authorization": "Bearer expired.token.here"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or expired session"

@pytest.mark.asyncio
async def test_public_paths():
    """Test that public paths are accessible without a token"""
    app = FastAPI()
    session_middleware = SessionMiddleware(testing=True)
    app.middleware("http")(session_middleware)
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Public endpoint should always work without token
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"} 