from pydantic import BaseModel, EmailStr
from app.models.user import UserRole


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: UserRole
    is_admin: bool
    is_active: bool
    department_id: int | None

    model_config = {"from_attributes": True}


# ---------- Auth ----------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SetupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class SetupStatusResponse(BaseModel):
    needs_setup: bool


# ---------- User management ----------
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    name: str | None = None
    password: str | None = None
    is_active: bool | None = None
