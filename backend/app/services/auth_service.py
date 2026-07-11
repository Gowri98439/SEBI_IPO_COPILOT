import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.models.token_blacklist import TokenBlacklist
from app.models.audit_event import AuditEvent
from app.schemas.auth import Token, UserCreate, AuthResponse
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class AuthService:
    @staticmethod
    async def log_failure(db: AsyncSession, email: str, action: str):
        audit_event = AuditEvent(
            action_category="AUTH",
            action=action,
            target_id=email,
            status="failure",
            workspace_id="00000000-0000-0000-0000-000000000000"  # default
        )
        db.add(audit_event)
        await db.commit()

    @staticmethod
    async def register(db: AsyncSession, user_create: UserCreate) -> AuthResponse:
        result = await db.execute(select(User).where(User.email == user_create.email))
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        user = User(
            email=user_create.email,
            password_hash=hash_password(user_create.password),
            full_name=user_create.full_name,
            role=user_create.role,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        # Store refresh token
        rt_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        db_refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=rt_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        db.add(db_refresh_token)
        await db.commit()
        
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user,
        )

    @staticmethod
    async def login(db: AsyncSession, email: str, password: str) -> AuthResponse:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):  # type: ignore
            await AuthService.log_failure(db, email, "LOGIN_FAILED")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        # Store refresh token
        rt_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        db_refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=rt_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        db.add(db_refresh_token)
        await db.commit()

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user,
        )

    @staticmethod
    async def refresh(db: AsyncSession, refresh_token: str) -> AuthResponse:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
            
        rt_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == rt_hash,
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False
            )
        )
        db_rt = result.scalar_one_or_none()
        if not db_rt:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is invalid or revoked",
            )
        
        db_rt.revoked = True
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        # Store new refresh token
        new_rt_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()
        new_db_refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=new_rt_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        db.add(new_db_refresh_token)
        await db.commit()
        
        return AuthResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            user=user,
        )

    @staticmethod
    async def logout(db: AsyncSession, access_token: str, refresh_token: str) -> None:
        try:
            access_payload = decode_token(access_token)
            jti = access_payload.get("jti")
            user_id = access_payload.get("sub")
            exp = access_payload.get("exp")
            if jti and user_id and exp:
                expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
                blacklist_entry = TokenBlacklist(
                    jti=jti,
                    user_id=user_id,
                    expires_at=expires_at
                )
                db.add(blacklist_entry)
        except HTTPException:
            pass  # if access token is already invalid, ignore

        if refresh_token:
            rt_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
            result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == rt_hash))
            db_rt = result.scalar_one_or_none()
            if db_rt:
                db_rt.revoked = True
        
        await db.commit()
