from fastapi import APIRouter, Depends

from services.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(get_current_user)])

@router.get("/test")
def test():
    return {"message": "ok"}
