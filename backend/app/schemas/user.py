from pydantic import BaseModel
from app.models.user import UserRole


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: UserRole
    department_id: int | None

    model_config = {"from_attributes": True}
