from sqlalchemy.orm import Session
from db import models

def seed_roles(db: Session) -> None:
    roles = ["admin", "user", "content-maker"]

    for role_name in roles:
        exists = db.query(models.UserRole).filter_by(name=role_name).first()
        if not exists:
            db.add(models.UserRole(name=role_name))

    db.commit()