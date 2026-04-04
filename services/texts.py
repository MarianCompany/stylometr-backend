from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from db import crud, models
from schemas.texts import ProfileTextCreate


def create_profile_text(
    db: Session,
    user: models.User,
    profile_id: int,
    data: ProfileTextCreate,
) -> models.Text:
    profile = crud.get_user_profile_by_id(db, user.id, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    content = data.content
    text = crud.create_text(
        db,
        content=content,
        user_id=user.id,
        char_count=len(content),
        file_id=None,
    )
    crud.link_text_to_profile(db, profile_id=profile.id, text_id=text.id)
    return text


def list_profile_texts(
    db: Session,
    user: models.User,
    profile_id: int,
) -> list[models.Text]:
    profile = crud.get_user_profile_by_id(db, user.id, profile_id)

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return crud.get_profile_texts(db, profile.id)


def get_profile_text(
    db: Session,
    user: models.User,
    profile_id: int,
    text_id: int,
) -> models.Text:
    profile = crud.get_user_profile_by_id(db, user.id, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    text = crud.get_profile_text_by_id(db, profile.id, text_id)
    if not text or text.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Text not found")
    return text


def delete_profile_text(
    db: Session,
    user: models.User,
    profile_id: int,
    text_id: int,
) -> None:
    profile = crud.get_user_profile_by_id(db, user.id, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    text = crud.get_profile_text_by_id(db, profile.id, text_id)
    if not text or text.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Text not found")
    link = crud.get_profile_text_link(db, profile.id, text.id)
    if link:
        crud.delete_profile_text_link(db, link)
    crud.delete_text(db, text)
