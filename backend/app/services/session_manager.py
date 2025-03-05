"""
Session management service for handling user authentication sessions
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid
import jwt
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.session import Session, SessionStatus, TokenType
from app.models.user import User
from app.utils.logging import get_logger

logger = get_logger(__name__)

class SessionManager:
    """Manages user authentication sessions with JWT tokens"""
    
    def __init__(self, settings: Dict[str, Any]):
        """
        Initialize the session manager
        
        Args:
            settings: Application settings dictionary containing:
                - jwt_secret: Secret key for JWT token signing
                - access_token_expire_minutes: Access token expiration time
                - refresh_token_expire_minutes: Refresh token expiration time
        """
        self.jwt_secret = settings["jwt_secret"]
        self.access_token_expire = int(settings.get("access_token_expire_minutes", 60))  # 1 hour
        self.refresh_token_expire = int(settings.get("refresh_token_expire_minutes", 10080))  # 7 days
        
    async def create_session(
        self,
        db: AsyncSession,
        telegram_id: Optional[int] = None,
        device_info: Optional[Dict] = None
    ) -> Session:
        """
        Create a new session with access and refresh tokens
        
        Args:
            db: Database session
            telegram_id: Optional Telegram user ID for pre-authenticated sessions
            device_info: Optional device information
            
        Returns:
            Created session object
        """
        # Create access token
        access_token_data = {
            "jti": str(uuid.uuid4()),
            "type": TokenType.ACCESS.value
        }
        if telegram_id:
            access_token_data["sub"] = str(telegram_id)
            
        access_token = self._create_jwt_token(
            access_token_data,
            expires_delta=timedelta(minutes=self.access_token_expire)
        )
        
        # Create refresh token
        refresh_token = self._create_jwt_token(
            {
                "jti": str(uuid.uuid4()),
                "type": TokenType.REFRESH.value,
                "sub": str(telegram_id) if telegram_id else None
            },
            expires_delta=timedelta(minutes=self.refresh_token_expire)
        )
        
        # Create session in database
        session = Session(
            telegram_id=telegram_id,
            status=SessionStatus.AUTHENTICATED if telegram_id else SessionStatus.PENDING,
            token=access_token,
            refresh_token=refresh_token,
            token_type=TokenType.ACCESS,
            expires_at=datetime.utcnow() + timedelta(minutes=self.access_token_expire),
            device_info=device_info or {}
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        logger.info(f"Created new session {session.id} for telegram_id={telegram_id}")
        return session
    
    async def verify_session(
        self,
        db: AsyncSession,
        token: str,
        token_type: TokenType = TokenType.ACCESS
    ) -> Session:
        """
        Verify and return session data
        
        Args:
            db: Database session
            token: JWT token to verify
            token_type: Type of token to verify (access or refresh)
            
        Returns:
            Verified session object
            
        Raises:
            HTTPException: If session is invalid or expired
        """
        try:
            # Verify JWT token
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            
            if payload.get("type") != token_type.value:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            # Get session from database
            stmt = select(Session).where(
                and_(
                    Session.token == token if token_type == TokenType.ACCESS else Session.refresh_token == token,
                    Session.expires_at > datetime.utcnow()
                )
            )
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session not found or expired"
                )
                
            # Update last activity
            session.update_activity()
            await db.commit()
            
            return session
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Session verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    async def refresh_session(
        self,
        db: AsyncSession,
        refresh_token: str
    ) -> Session:
        """
        Create new access token using refresh token
        
        Args:
            db: Database session
            refresh_token: Refresh token to use
            
        Returns:
            Updated session object with new access token
            
        Raises:
            HTTPException: If refresh token is invalid or expired
        """
        # Verify refresh token
        session = await self.verify_session(db, refresh_token, TokenType.REFRESH)
        
        # Create new access token
        new_access_token = self._create_jwt_token(
            {
                "jti": str(uuid.uuid4()),
                "type": TokenType.ACCESS.value,
                "sub": str(session.telegram_id) if session.telegram_id else None
            },
            expires_delta=timedelta(minutes=self.access_token_expire)
        )
        
        # Update session
        session.token = new_access_token
        session.expires_at = datetime.utcnow() + timedelta(minutes=self.access_token_expire)
        session.update_activity()
        
        await db.commit()
        await db.refresh(session)
        
        logger.info(f"Refreshed session {session.id}")
        return session
    
    async def invalidate_session(
        self,
        db: AsyncSession,
        token: str,
        token_type: TokenType = TokenType.ACCESS
    ) -> None:
        """
        Invalidate a session
        
        Args:
            db: Database session
            token: Token to invalidate
            token_type: Type of token to invalidate
        """
        stmt = select(Session).where(
            Session.token == token if token_type == TokenType.ACCESS else Session.refresh_token == token
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if session:
            session.status = SessionStatus.EXPIRED
            session.expires_at = datetime.utcnow()
            await db.commit()
            logger.info(f"Invalidated session {session.id}")
    
    def _create_jwt_token(self, data: Dict[str, Any], expires_delta: timedelta) -> str:
        """
        Create a new JWT token
        
        Args:
            data: Data to encode in the token
            expires_delta: Token expiration time
            
        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow()
        })
        return jwt.encode(to_encode, self.jwt_secret, algorithm="HS256") 