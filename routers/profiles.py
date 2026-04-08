from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy.orm import Session

from db import models
from db.session import get_db
from schemas.comparisons import ComparisonResponse
from schemas.profiles import ProfileCreate, ProfileListItem, ProfileMetricsRead, ProfileRead, ProfileUpdate
from schemas.texts import ProfileTextCreate, ProfileTextListItem, ProfileTextRead
from services.auth import get_current_user, get_current_user_optional
from services import comparisons as comparisons_service
from services import profiles as profiles_service
from services import texts as texts_service

router = APIRouter(
    prefix="/profiles",
    tags=["profiles"],
)


@router.post("", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: ProfileCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return profiles_service.create_profile(db, current_user, payload)


@router.get("", response_model=list[ProfileListItem])
def list_profiles(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return profiles_service.list_profiles(db, current_user)


@router.get("/{profile_id}", response_model=ProfileRead)
def get_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return profiles_service.get_profile(db, current_user, profile_id)


@router.get("/{profile_id}/metrics", response_model=ProfileMetricsRead)
def get_profile_metrics(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return profiles_service.get_profile_metrics(db, current_user, profile_id)


@router.post("/{profile_id}/compare", response_model=ComparisonResponse)
def compare_profile(
    profile_id: int,
    text: str | None = Form(default=None),
    text_id: int | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user_optional),
):
    result = comparisons_service.compare_text_to_profile(
        db,
        profile_id,
        current_user,
        text=text,
        file=file,
        text_id=text_id,
    )
    return ComparisonResponse(**result)


@router.patch("/{profile_id}", response_model=ProfileRead)
def update_profile(
    profile_id: int,
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return profiles_service.update_profile(db, current_user, profile_id, payload)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    profiles_service.delete_profile(db, current_user, profile_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{profile_id}/texts", response_model=ProfileTextRead, status_code=status.HTTP_201_CREATED)
def create_profile_text(
    profile_id: int,
    payload: ProfileTextCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return texts_service.create_profile_text(db, current_user, profile_id, payload)


@router.get("/{profile_id}/texts", response_model=list[ProfileTextListItem])
def list_profile_texts(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return texts_service.list_profile_texts(db, current_user, profile_id)


@router.get("/{profile_id}/texts/{text_id}", response_model=ProfileTextRead)
def get_profile_text(
    profile_id: int,
    text_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return texts_service.get_profile_text(db, current_user, profile_id, text_id)


@router.delete("/{profile_id}/texts/{text_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile_text(
    profile_id: int,
    text_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    texts_service.delete_profile_text(db, current_user, profile_id, text_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
