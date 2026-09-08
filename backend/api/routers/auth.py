from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.common.db import get_db
from backend.common.models import AdminUser
from backend.common.schemas import (
    AdminUserCreate,
    AdminUserResponse,
    LoginRequest,
    TokenResponse,
)
from backend.common.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: AdminUserCreate, db: Annotated[Session, Depends(get_db)]) -> AdminUser:
    existing = db.query(AdminUser).filter(AdminUser.email == payload.email).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user = AdminUser(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    user = db.query(AdminUser).filter(AdminUser.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    return TokenResponse(access_token=create_access_token(subject=user.email))
