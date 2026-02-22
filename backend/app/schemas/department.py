from pydantic import BaseModel


class DepartmentOut(BaseModel):
    id: int
    name: str
    is_active: bool

    model_config = {"from_attributes": True}


class DepartmentCreate(BaseModel):
    name: str
    is_active: bool = True


class DepartmentUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
