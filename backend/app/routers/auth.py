from fastapi import APIRouter, Depends
from app.auth import get_current_user
from app.models.user import User
from app.schemas.user import UserOut

router = APIRouter(tags=["auth"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
