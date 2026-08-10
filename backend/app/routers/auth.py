from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user, oauth2_scheme
from app.models.user import User
from app.schemas.auth import Token, TokenRefresh, UserCreate, UserLogin, UserResponse, AuthResponse
from app.services.auth_service import AuthService
from app.security.rate_limiter import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, status_code=201)
@limiter.limit("10/minute")
async def register(
    request: Request,
    user_create: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    user = await AuthService.register(db, user_create)
    return user  # type: ignore[return-value]


@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    return await AuthService.login(db, credentials.email, credentials.password)


@router.post("/refresh", response_model=AuthResponse)
@limiter.limit("20/minute")
async def refresh_token(
    request: Request,
    body: TokenRefresh,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    return await AuthService.refresh(db, body.refresh_token)


@router.post("/logout")
async def logout(
    body: TokenRefresh,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    await AuthService.logout(db, access_token=token, refresh_token=body.refresh_token)
    return {"detail": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return current_user  # type: ignore[return-value]
