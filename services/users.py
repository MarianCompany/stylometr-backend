from sqlalchemy.orm import Session

from db import crud, models
from schemas.users import UserRegister
from services.auth import hash_password


def register_user(db: Session, data: UserRegister) -> models.User:
    existing = crud.get_user_by_email(db, data.email)
    if existing:
        raise ValueError("email_taken")
    password_hash = hash_password(data.password)
    return crud.create_user(
        db=db,
        email=data.email,
        nickname=data.nickname,
        password_hash=password_hash,
    )
