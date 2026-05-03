from fastapi import APIRouter

from admin.routers import logs, moderation, users, profiles

admin_router = APIRouter(prefix="/admin", tags=["admin"])
admin_router.include_router(users.router)
admin_router.include_router(moderation.router)
admin_router.include_router(logs.router)
admin_router.include_router(profiles.router)
