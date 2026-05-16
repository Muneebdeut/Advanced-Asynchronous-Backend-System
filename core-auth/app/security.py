from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_algorithm = "HS256"
_secrets = {
    "access": settings.ACCESS_TOKEN_SECRET,
    "refresh": settings.REFRESH_TOKEN_SECRET,
}
_expires = {
    "access": timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    "refresh": timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
}

TokenType = Literal["access", "refresh"]


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_token(subject: str, token_type: TokenType) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + _expires[token_type],
    }
    return jwt.encode(payload, _secrets[token_type], algorithm=_algorithm)


def decode_token(token: str, token_type: TokenType) -> dict:
    payload = jwt.decode(token, _secrets[token_type], algorithms=[_algorithm])
    if payload.get("type") != token_type:
        raise JWTError("Token type mismatch")
    return payload
