from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from db import crud, models
from db.session import get_db
from schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    TokenPair,
)
from schemas.users import UserRead, UserRegister
from services import auth as auth_service
from services import users as users_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegister, db: Session = Depends(get_db)):
    try:
        user = users_service.register_user(db, payload)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    return user


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(db, payload.email, payload.password)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = auth_service.create_access_token(user.id)
    refresh_token, jti, expires_at = auth_service.create_refresh_token(user.id)
    auth_service.store_refresh_token(
        db,
        user_id=user.id,
        token=refresh_token,
        jti=jti,
        expires_at=expires_at,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_access_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_payload, token_record = auth_service.verify_refresh_token(db, payload.refresh_token)
    if token_payload.sub != str(token_record.user_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    access_token = auth_service.create_access_token(token_record.user_id)
    return AccessTokenResponse(access_token=access_token)


@router.post("/logout")
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    _, token_record = auth_service.verify_refresh_token(db, payload.refresh_token)
    crud.revoke_refresh_token(db, token_record)
    return {"status": "ok"}


@router.get("/me", response_model=UserRead)
def get_me(current_user: models.User = Depends(auth_service.get_current_user)):
    return current_user
