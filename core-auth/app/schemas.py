from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserRegistrationResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenExchangeResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class StandardActionResponse(BaseModel):
    detail: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str
