from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import (
    LoginRequest,
    LoginResponse,
    SetupRequest,
    SetupStatusResponse,
    UserOut,
)

router = APIRouter(tags=["auth"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Ungültige Anmeldedaten.")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Ungültige Anmeldedaten.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Benutzerkonto deaktiviert.")

    token = create_access_token(user.id, user.email)
    return LoginResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/setup-status", response_model=SetupStatusResponse)
def setup_status(db: Session = Depends(get_db)):
    has_moderator = (
        db.query(User)
        .filter(User.role.in_([UserRole.moderator, UserRole.marketing]))
        .first()
        is None
    )
    return SetupStatusResponse(needs_setup=has_moderator)


@router.post("/setup", response_model=LoginResponse, status_code=201)
def setup(body: SetupRequest, db: Session = Depends(get_db)):
    existing = (
        db.query(User)
        .filter(User.role.in_([UserRole.moderator, UserRole.marketing]))
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Ersteinrichtung bereits abgeschlossen.",
        )

    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="E-Mail-Adresse bereits vergeben.")

    user = User(
        email=body.email,
        name=body.name,
        role=UserRole.moderator,
        password_hash=hash_password(body.password),
        is_admin=True,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.email)
    return LoginResponse(access_token=token, user=UserOut.model_validate(user))
