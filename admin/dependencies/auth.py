from fastapi import Depends, HTTPException, status

from db import models
from services.auth import get_current_user



def _has_admin_role(user: models.User) -> bool:
    if bool(getattr(user, "is_admin", False)):
        return True
    role = getattr(user, "role", None)
    role_name = getattr(role, "name", None)
    return role_name == "admin"


def get_current_admin_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not _has_admin_role(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
