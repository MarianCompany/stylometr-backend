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


def create_profile(
    db: Session,
    user_id: int,
    name: str,
) -> models.AuthorProfile:
    profile = models.AuthorProfile(
        user_id=user_id,
        name=name,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def get_profile_by_id(db: Session, profile_id: int) -> models.AuthorProfile | None:
    return db.query(models.AuthorProfile).filter(models.AuthorProfile.id == profile_id).first()


def get_user_profile_by_id(
    db: Session,
    user_id: int,
    profile_id: int,
) -> models.AuthorProfile | None:
    return (
        db.query(models.AuthorProfile)
        .filter(
            models.AuthorProfile.id == profile_id,
            models.AuthorProfile.user_id == user_id,
        )
        .first()
    )


def get_profiles_by_user_id(db: Session, user_id: int) -> list[models.AuthorProfile]:
    return (
        db.query(models.AuthorProfile)
        .filter(models.AuthorProfile.user_id == user_id)
        .order_by(models.AuthorProfile.created_at.desc())
        .all()
    )


def update_profile(db: Session, profile: models.AuthorProfile, data: dict) -> models.AuthorProfile:
    for key, value in data.items():
        setattr(profile, key, value)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def delete_profile(db: Session, profile: models.AuthorProfile) -> None:
    db.delete(profile)
    db.commit()


def create_profile_metrics(
    db: Session,
    profile_id: int,
    metrics_version: int = 1,
    core_metrics: dict | None = None,
    additional_metrics: dict | None = None,
) -> models.ProfileMetrics:
    metrics = models.ProfileMetrics(
        profile_id=profile_id,
        metrics_version=metrics_version,
        core_metrics=core_metrics,
        additional_metrics=additional_metrics,
    )
    db.add(metrics)
    db.commit()
    db.refresh(metrics)
    return metrics


def get_profile_metrics_by_profile_id(
    db: Session,
    profile_id: int,
) -> models.ProfileMetrics | None:
    return (
        db.query(models.ProfileMetrics)
        .filter(models.ProfileMetrics.profile_id == profile_id)
        .first()
    )


def update_profile_metrics(
    db: Session,
    metrics: models.ProfileMetrics,
    data: dict,
) -> models.ProfileMetrics:
    for key, value in data.items():
        setattr(metrics, key, value)
    db.add(metrics)
    db.commit()
    db.refresh(metrics)
    return metrics


def delete_profile_metrics(db: Session, metrics: models.ProfileMetrics) -> None:
    db.delete(metrics)
    db.commit()


def create_text(
    db: Session,
    content: str,
    user_id: int,
    char_count: int,
    file_id: int | None = None,
) -> models.Text:
    text = models.Text(
        content=content,
        user_id=user_id,
        char_count=char_count,
        file_id=file_id,
    )
    db.add(text)
    db.commit()
    db.refresh(text)
    return text


def create_text_metrics(
    db: Session,
    text_id: int,
    metrics: dict,
) -> models.TextMetrics:
    payload = dict(metrics)
    payload["text_id"] = text_id
    record = models.TextMetrics(**payload)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_text_metrics_by_text_id(db: Session, text_id: int) -> models.TextMetrics | None:
    return db.query(models.TextMetrics).filter(models.TextMetrics.text_id == text_id).first()


def update_text_metrics(
    db: Session,
    metrics: models.TextMetrics,
    data: dict,
) -> models.TextMetrics:
    for key, value in data.items():
        setattr(metrics, key, value)
    db.add(metrics)
    db.commit()
    db.refresh(metrics)
    return metrics


def get_text_by_id(db: Session, text_id: int) -> models.Text | None:
    return db.query(models.Text).filter(models.Text.id == text_id).first()


def delete_text(db: Session, text: models.Text) -> None:
    db.delete(text)
    db.commit()


def link_text_to_profile(
    db: Session,
    profile_id: int,
    text_id: int,
) -> models.AuthorProfileText:
    link = models.AuthorProfileText(profile_id=profile_id, text_id=text_id)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def get_profile_texts(db: Session, profile_id: int) -> list[models.Text]:
    return (
        db.query(models.Text)
        .join(models.AuthorProfileText, models.AuthorProfileText.text_id == models.Text.id)
        .filter(models.AuthorProfileText.profile_id == profile_id)
        .order_by(models.AuthorProfileText.created_at.desc())
        .all()
    )


def get_profile_text_by_id(
    db: Session,
    profile_id: int,
    text_id: int,
) -> models.Text | None:
    return (
        db.query(models.Text)
        .join(models.AuthorProfileText, models.AuthorProfileText.text_id == models.Text.id)
        .filter(
            models.AuthorProfileText.profile_id == profile_id,
            models.Text.id == text_id,
        )
        .first()
    )


def get_profile_text_link(
    db: Session,
    profile_id: int,
    text_id: int,
) -> models.AuthorProfileText | None:
    return (
        db.query(models.AuthorProfileText)
        .filter(
            models.AuthorProfileText.profile_id == profile_id,
            models.AuthorProfileText.text_id == text_id,
        )
        .first()
    )


def delete_profile_text_link(db: Session, link: models.AuthorProfileText) -> None:
    db.delete(link)
    db.commit()


def get_profile_ids_by_text_id(db: Session, text_id: int) -> list[int]:
    results = (
        db.query(models.AuthorProfileText.profile_id)
        .filter(models.AuthorProfileText.text_id == text_id)
        .distinct()
        .all()
    )
    return [profile_id for (profile_id,) in results]


def get_profile_text_metrics(db: Session, profile_id: int) -> list[models.TextMetrics]:
    return (
        db.query(models.TextMetrics)
        .join(models.Text, models.TextMetrics.text_id == models.Text.id)
        .join(models.AuthorProfileText, models.AuthorProfileText.text_id == models.Text.id)
        .filter(models.AuthorProfileText.profile_id == profile_id)
        .all()
    )
