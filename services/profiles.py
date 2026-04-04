from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from db import crud, models
from schemas.profiles import ProfileCreate, ProfileUpdate


def create_profile(db: Session, user: models.User, data: ProfileCreate) -> models.AuthorProfile:
    profile = crud.create_profile(db, user_id=user.id, name=data.name)
    return profile


def list_profiles(db: Session, user: models.User) -> list[models.AuthorProfile]:
    return crud.get_profiles_by_user_id(db, user.id)


def get_profile(db: Session, user: models.User, profile_id: int) -> models.AuthorProfile:
    profile = crud.get_user_profile_by_id(db, user.id, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


def update_profile(
    db: Session,
    user: models.User,
    profile_id: int,
    data: ProfileUpdate,
) -> models.AuthorProfile:
    profile = crud.get_user_profile_by_id(db, user.id, profile_id)

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return profile

    return crud.update_profile(db, profile, update_data)


def delete_profile(db: Session, user: models.User, profile_id: int) -> None:
    profile = crud.get_user_profile_by_id(db, user.id, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    metrics = crud.get_profile_metrics_by_profile_id(db, profile.id)
    if metrics:
        crud.delete_profile_metrics(db, metrics)
    crud.delete_profile(db, profile)
