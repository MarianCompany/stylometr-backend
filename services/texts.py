from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from analytics.features import extract_text_metrics
from db import crud, models
from schemas.texts import ProfileTextCreate
from services import profile_metrics as profile_metrics_service


def create_profile_text(
    db: Session,
    user: models.User,
    profile_id: int,
    data: ProfileTextCreate,
) -> models.Text:
    profile = crud.get_user_profile_by_id(db, user.id, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль не найден")
    content = data.content
    text = crud.create_text(
        db,
        content=content,
        user_id=user.id,
        char_count=len(content),
        file_id=None,
    )
    crud.link_text_to_profile(db, profile_id=profile.id, text_id=text.id)
    metrics_payload = extract_text_metrics(content)
    crud.create_text_metrics(db, text_id=text.id, metrics=metrics_payload)
    profile_metrics_service.recalculate_profile_metrics(db, profile.id)
    return text


def list_profile_texts(
    db: Session,
    user: models.User,
    profile_id: int,
) -> list[models.Text]:
    profile = crud.get_user_profile_by_id(db, user.id, profile_id)

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль не найден")
    return crud.get_profile_texts(db, profile.id)


def get_profile_text(
    db: Session,
    user: models.User,
    profile_id: int,
    text_id: int,
) -> models.Text:
    profile = crud.get_user_profile_by_id(db, user.id, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль не найден")
    text = crud.get_profile_text_by_id(db, profile.id, text_id)
    if not text or text.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Текст не найден")
    return text


def delete_profile_text(
    db: Session,
    user: models.User,
    profile_id: int,
    text_id: int,
) -> None:
    profile = crud.get_user_profile_by_id(db, user.id, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль не найден")
    text = crud.get_profile_text_by_id(db, profile.id, text_id)
    if not text or text.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Текст не найден")
    profile_ids = crud.get_profile_ids_by_text_id(db, text.id)
    link = crud.get_profile_text_link(db, profile.id, text.id)
    if link:
        crud.delete_profile_text_link(db, link)
    crud.delete_text(db, text)
    for pid in profile_ids:
        profile_metrics_service.recalculate_profile_metrics(db, pid)


def reprocess_text_metrics(db: Session, text: models.Text) -> models.TextMetrics:
    metrics_payload = extract_text_metrics(text.content)
    existing = crud.get_text_metrics_by_text_id(db, text.id)
    if existing:
        metrics = crud.update_text_metrics(db, existing, metrics_payload)
    else:
        metrics = crud.create_text_metrics(db, text_id=text.id, metrics=metrics_payload)
    profile_metrics_service.recalculate_profiles_for_text(db, text.id)
    return metrics
