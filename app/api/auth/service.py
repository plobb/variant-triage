from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.schemas import TokenData
from app.core.config import settings
from app.db.models import User

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_access_token(
    data: dict[str, object],
    expires_delta: timedelta | None = None,
) -> str:
    to_encode: dict[str, object] = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta if expires_delta is not None else timedelta(minutes=30)
    )
    to_encode["exp"] = expire
    encoded: str = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded


async def get_user_by_email(email: str, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def authenticate_user(
    email: str, password: str, db: AsyncSession
) -> User | None:
    user = await get_user_by_email(email, db)
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(token: str, db: AsyncSession) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload: dict[str, object] = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email: object = payload.get("sub")
        if not isinstance(email, str):
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError as exc:
        raise credentials_exception from exc

    if token_data.email is None:
        raise credentials_exception
    user = await get_user_by_email(token_data.email, db)
    if user is None:
        raise credentials_exception
    return user
