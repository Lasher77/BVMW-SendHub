from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_marketing
from app.database import get_db
from app.models.department import Department
from app.models.user import User
from app.schemas.department import DepartmentOut, DepartmentCreate, DepartmentUpdate

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentOut])
def list_departments(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.query(Department).order_by(Department.name).all()


@router.post("", response_model=DepartmentOut, status_code=201)
def create_department(
    body: DepartmentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_marketing),
):
    if db.query(Department).filter(Department.name == body.name).first():
        raise HTTPException(status_code=409, detail="Abteilung mit diesem Namen existiert bereits.")
    dept = Department(name=body.name, is_active=body.is_active)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.patch("/{dept_id}", response_model=DepartmentOut)
def update_department(
    dept_id: int,
    body: DepartmentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_marketing),
):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Abteilung nicht gefunden.")
    if body.name is not None:
        dept.name = body.name
    if body.is_active is not None:
        dept.is_active = body.is_active
    db.commit()
    db.refresh(dept)
    return dept
