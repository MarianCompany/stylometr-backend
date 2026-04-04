from datetime import datetime
from sqlalchemy.orm import Session

from db import models


def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> models.User | None:
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(
    db: Session,
    email: str,
    nickname: str,
    password_hash: str,
    role_id: int | None = None,
) -> models.User:
    user = models.User(
        email=email,
        nickname=nickname,
        password_hash=password_hash,
        role_id=role_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_refresh_token(
    db: Session,
    user_id: int,
    token_hash: str,
    jti: str,
    expires_at: datetime,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> models.RefreshToken:
    token = models.RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        jti=jti,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def get_refresh_token_by_jti(db: Session, jti: str) -> models.RefreshToken | None:
    return db.query(models.RefreshToken).filter(models.RefreshToken.jti == jti).first()


def revoke_refresh_token(db: Session, token: models.RefreshToken) -> models.RefreshToken:
    token.revoked_at = datetime.utcnow()
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def revoke_all_user_refresh_tokens(db: Session, user_id: int) -> int:
    now = datetime.utcnow()
    result = (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.user_id == user_id, models.RefreshToken.revoked_at.is_(None))
        .update({"revoked_at": now})
    )
    db.commit()
    return result
