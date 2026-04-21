from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.schemas import Token, UserCreate, UserResponse
from app.api.auth.service import (
    authenticate_user,
    create_access_token,
    get_user_by_email,
    hash_password,
)
from app.api.deps import get_db
from app.core.config import settings
from app.db.models import User

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    description="Register a new user account. Returns user details (no token).",
)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> User:
    existing = await get_user_by_email(user_in.email, db)
    if existing is not None:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post(
    "/token",
    response_model=Token,
    description="Obtain a JWT Bearer token using email and password (OAuth2 form).",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    user = await authenticate_user(form_data.username, form_data.password, db)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token, token_type="bearer")
