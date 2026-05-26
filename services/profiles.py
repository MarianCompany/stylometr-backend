from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from db import crud, models
from schemas.profiles import ProfileCreate, ProfileMetricsRead, ProfileUpdate
from services import profile_metrics as profile_metrics_service


def create_profile(db: Session, user: models.User, data: ProfileCreate) -> models.AuthorProfile:
    profile = crud.create_profile(db, user_id=user.id, name=data.name)
    profile_metrics_service.recalculate_profile_metrics(db, profile.id)
    return profile


def list_profiles(db: Session, user: models.User) -> list[models.AuthorProfile]:
    return crud.get_profiles_by_user_id(db, user.id)


def get_profile(db: Session, user: models.User, profile_id: int) -> models.AuthorProfile:
    profile = crud.get_user_profile_by_id(db, user.id, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль не найден")
    return profile


def update_profile(
    db: Session,
    user: models.User,
    profile_id: int,
    data: ProfileUpdate,
) -> models.AuthorProfile:
    profile = crud.get_user_profile_by_id(db, user.id, profile_id)

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль не найден")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return profile

    return crud.update_profile(db, profile, update_data)


def delete_profile(db: Session, user: models.User, profile_id: int) -> None:
    profile = crud.get_user_profile_by_id(db, user.id, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль не найден")
    metrics = crud.get_profile_metrics_by_profile_id(db, profile.id)
    if metrics:
        crud.delete_profile_metrics(db, metrics)
    crud.delete_profile(db, profile)


def get_profile_metrics(
    db: Session,
    user: models.User,
    profile_id: int,
) -> ProfileMetricsRead:
    profile = crud.get_user_profile_by_id(db, user.id, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль не найден")
    metrics = crud.get_profile_metrics_by_profile_id(db, profile.id)
    if not metrics:
        metrics = profile_metrics_service.recalculate_profile_metrics(db, profile.id)
    return ProfileMetricsRead(
        profile_id=profile.id,
        profile_name=profile.name,
        metrics_version=metrics.metrics_version,
        core_metrics=metrics.core_metrics,
        additional_metrics=metrics.additional_metrics,
        created_at=metrics.created_at,
        updated_at=metrics.updated_at,
    )
