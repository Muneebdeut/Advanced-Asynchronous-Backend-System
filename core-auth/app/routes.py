from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_redis
from app.deps import get_current_user
from app.models import User
from app.schemas import (
    RefreshTokenRequest,
    StandardActionResponse,
    TokenExchangeResponse,
    UserCreate,
    UserLogin,
    UserRegistrationResponse,
)
from app.security import create_token, decode_token, verify_password
from app.services import blacklist_token, create_user, get_user_by_email

api = APIRouter(prefix="/api/v1")
auth = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer()


@api.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    if not await get_redis().ping():
        raise RuntimeError("Redis ping failed")
    return {"status": "ok"}


@auth.post("/register", response_model=UserRegistrationResponse, status_code=201)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    if await get_user_by_email(db, payload.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    return await create_user(db, payload)


@auth.post("/login", response_model=TokenExchangeResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")
    return TokenExchangeResponse(
        access_token=create_token(user.email, "access"),
        refresh_token=create_token(user.email, "refresh"),
    )


@auth.get("/me", response_model=UserRegistrationResponse)
async def me(user: User = Depends(get_current_user)):
    return user


@auth.post("/refresh", response_model=TokenExchangeResponse)
async def refresh(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token, "refresh")
        email = payload.get("sub")
        if not email:
            raise JWTError("Missing subject")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = await get_user_by_email(db, email)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return TokenExchangeResponse(
        access_token=create_token(email, "access"),
        refresh_token=create_token(email, "refresh"),
    )


@auth.post("/logout", response_model=StandardActionResponse)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    _user: User = Depends(get_current_user),
):
    await blacklist_token(credentials.credentials)
    return StandardActionResponse(detail="Logged out")


api.include_router(auth)
