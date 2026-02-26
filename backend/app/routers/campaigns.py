from datetime import datetime, timezone
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_asset import CampaignAsset
from app.models.campaign_comment import CampaignComment
from app.models.campaign_file import CampaignFile
from app.models.campaign_move_log import CampaignMoveLog
from app.models.department import Department
from app.models.user import User, UserRole
from app.schemas.campaign import (
    CampaignAssetOut,
    CampaignListItem,
    CampaignOut,
    CampaignStatusUpdate,
    CommentCreate,
    CampaignCommentOut,
    CampaignFileOut,
)
from app.services.campaign_service import (
    MARKETING_EDITABLE_STATUSES,
    REQUESTER_EDITABLE_STATUSES,
    apply_status_transition,
    save_asset,
    save_pdf,
)
from app.services.notification_service import (
    notify_new_campaign,
    notify_new_comment,
    notify_status_change,
)
from app.services.schedule_service import next_available, validate_email_slot
from app.storage import storage

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _load_campaign(db: Session, campaign_id: int) -> Campaign:
    c = (
        db.query(Campaign)
        .options(
            joinedload(Campaign.department),
            joinedload(Campaign.creator),
            joinedload(Campaign.files).joinedload(CampaignFile.uploaded_by),
            joinedload(Campaign.assets).joinedload(CampaignAsset.uploaded_by),
            joinedload(Campaign.comments).joinedload(CampaignComment.author),
            joinedload(Campaign.move_logs).joinedload(CampaignMoveLog.moved_by),
        )
        .filter(Campaign.id == campaign_id)
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Kampagne nicht gefunden.")
    return c


# --------------------------------------------------------------------------- #
# List
# --------------------------------------------------------------------------- #
@router.get("", response_model=list[CampaignListItem])
def list_campaigns(
    status: Optional[str] = Query(default=None),
    department_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Campaign).options(
        joinedload(Campaign.department),
        joinedload(Campaign.creator),
    )
    # Requester sees only own campaigns
    if current_user.role == UserRole.requester:
        q = q.filter(Campaign.created_by_id == current_user.id)
    if status:
        q = q.filter(Campaign.status == status)
    if department_id:
        q = q.filter(Campaign.department_id == department_id)
    return q.order_by(Campaign.created_at.desc()).all()


# --------------------------------------------------------------------------- #
# Detail
# --------------------------------------------------------------------------- #
@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = _load_campaign(db, campaign_id)
    if current_user.role == UserRole.requester and c.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")
    return c


# --------------------------------------------------------------------------- #
# Create (multipart)
# --------------------------------------------------------------------------- #
@router.post("", response_model=CampaignOut, status_code=201)
def create_campaign(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    department_id: int = Form(...),
    send_at: Optional[str] = Form(default=None),
    pdf: UploadFile = File(...),
    assets: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate department
    dept = db.query(Department).filter(
        Department.id == department_id, Department.is_active == True
    ).first()
    if not dept:
        raise HTTPException(status_code=422, detail="Ungültige oder inaktive Abteilung.")

    # Determine send_at
    if send_at:
        try:
            parsed_send_at = datetime.fromisoformat(send_at)
        except ValueError:
            raise HTTPException(status_code=422, detail="Ungültiges Datumsformat für send_at.")
    else:
        parsed_send_at = next_available(db, channel="email")

    # Validate slot against already scheduled/approved/sent campaigns
    validate_email_slot(db, parsed_send_at)

    # Create campaign record first (need ID for file paths)
    campaign = Campaign(
        title=title,
        channel="email",
        department_id=department_id,
        status=CampaignStatus.submitted,
        send_at=parsed_send_at,
        created_by_id=current_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(campaign)
    db.flush()  # get campaign.id

    # Save PDF
    save_pdf(db, campaign, pdf, current_user)

    # Save optional assets (one by one, no ZIP)
    for asset_file in assets:
        if asset_file.filename:
            save_asset(db, campaign, asset_file, current_user)

    db.commit()
    loaded = _load_campaign(db, campaign.id)
    background_tasks.add_task(notify_new_campaign, db, loaded, current_user)
    return loaded


# --------------------------------------------------------------------------- #
# Status update / rescheduling
# --------------------------------------------------------------------------- #
@router.patch("/{campaign_id}", response_model=CampaignOut)
def update_campaign(
    campaign_id: int,
    body: CampaignStatusUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaign = _load_campaign(db, campaign_id)

    if current_user.role == UserRole.requester and campaign.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")

    # send_at-only update (no status transition)
    if body.status is None:
        if body.send_at is None:
            raise HTTPException(status_code=422, detail="send_at erforderlich wenn kein Status angegeben.")
        allowed = MARKETING_EDITABLE_STATUSES if current_user.role == UserRole.marketing else REQUESTER_EDITABLE_STATUSES
        if campaign.status not in allowed:
            raise HTTPException(status_code=403, detail="Termin kann in diesem Status nicht geändert werden.")
        validate_email_slot(db, body.send_at, campaign_id=campaign.id)
        campaign.send_at = body.send_at
        campaign.updated_at = datetime.now(timezone.utc)
        db.commit()
        return _load_campaign(db, campaign_id)

    old_status = campaign.status
    apply_status_transition(
        db,
        campaign,
        body.status,
        current_user,
        send_at=body.send_at,
        reason=body.reason,
    )
    db.commit()
    loaded = _load_campaign(db, campaign_id)
    background_tasks.add_task(
        notify_status_change, db, loaded, old_status, body.status, current_user, body.reason,
    )
    return loaded


# --------------------------------------------------------------------------- #
# Upload new PDF version
# --------------------------------------------------------------------------- #
@router.post("/{campaign_id}/files", response_model=CampaignFileOut, status_code=201)
def upload_new_pdf(
    campaign_id: int,
    pdf: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaign = _load_campaign(db, campaign_id)

    if current_user.role == UserRole.requester and campaign.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")

    allowed = MARKETING_EDITABLE_STATUSES if current_user.role == UserRole.marketing else REQUESTER_EDITABLE_STATUSES
    if campaign.status not in allowed:
        raise HTTPException(status_code=403, detail="Dateien können in diesem Status nicht mehr geändert werden.")

    cf = save_pdf(db, campaign, pdf, current_user)
    db.commit()
    db.refresh(cf)

    # Load the user relationship
    from app.models.user import User as UserModel
    cf.uploaded_by = db.query(UserModel).filter(UserModel.id == cf.uploaded_by_id).first()
    return cf


# --------------------------------------------------------------------------- #
# Assets
# --------------------------------------------------------------------------- #
@router.post("/{campaign_id}/assets", response_model=CampaignAssetOut, status_code=201)
def upload_asset(
    campaign_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaign = _load_campaign(db, campaign_id)
    if current_user.role == UserRole.requester and campaign.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")

    asset = save_asset(db, campaign, file, current_user)
    db.commit()
    db.refresh(asset)
    asset.uploaded_by = db.query(User).filter(User.id == asset.uploaded_by_id).first()
    return asset


@router.get("/{campaign_id}/assets", response_model=list[CampaignAssetOut])
def list_assets(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaign = _load_campaign(db, campaign_id)
    if current_user.role == UserRole.requester and campaign.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")
    assets = (
        db.query(CampaignAsset)
        .options(joinedload(CampaignAsset.uploaded_by))
        .filter(
            CampaignAsset.campaign_id == campaign_id,
            CampaignAsset.is_deleted == False,
        )
        .all()
    )
    return assets


@router.delete("/{campaign_id}/assets/{asset_id}", status_code=204)
def soft_delete_asset(
    campaign_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaign = _load_campaign(db, campaign_id)

    if current_user.role == UserRole.requester and campaign.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")

    allowed = MARKETING_EDITABLE_STATUSES if current_user.role == UserRole.marketing else REQUESTER_EDITABLE_STATUSES
    if campaign.status not in allowed:
        raise HTTPException(status_code=403, detail="Dateien können in diesem Status nicht mehr geändert werden.")

    asset = db.query(CampaignAsset).filter(
        CampaignAsset.id == asset_id,
        CampaignAsset.campaign_id == campaign_id,
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset nicht gefunden.")
    asset.is_deleted = True
    db.commit()


# --------------------------------------------------------------------------- #
# Download asset
# --------------------------------------------------------------------------- #
@router.get("/assets/{asset_id}/download")
def download_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = db.query(CampaignAsset).filter(CampaignAsset.id == asset_id).first()
    if not asset or asset.is_deleted:
        raise HTTPException(status_code=404, detail="Asset nicht gefunden.")

    # Check access
    campaign = db.query(Campaign).filter(Campaign.id == asset.campaign_id).first()
    if current_user.role == UserRole.requester and campaign.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")

    data = storage.read(asset.storage_path)
    return Response(
        content=data,
        media_type=asset.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{asset.original_filename}"'},
    )


# --------------------------------------------------------------------------- #
# Download PDF
# --------------------------------------------------------------------------- #
@router.get("/{campaign_id}/files/{file_id}/download")
def download_pdf(
    campaign_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.campaign_file import CampaignFile
    cf = db.query(CampaignFile).filter(
        CampaignFile.id == file_id,
        CampaignFile.campaign_id == campaign_id,
    ).first()
    if not cf:
        raise HTTPException(status_code=404, detail="Datei nicht gefunden.")

    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if current_user.role == UserRole.requester and campaign.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")

    data = storage.read(cf.storage_path)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{cf.original_filename}"'},
    )


# --------------------------------------------------------------------------- #
# Comments
# --------------------------------------------------------------------------- #
@router.post("/{campaign_id}/comments", response_model=CampaignCommentOut, status_code=201)
def add_comment(
    campaign_id: int,
    body: CommentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaign = _load_campaign(db, campaign_id)
    if current_user.role == UserRole.requester and campaign.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Zugriff verweigert.")

    comment = CampaignComment(
        campaign_id=campaign_id,
        author_id=current_user.id,
        text=body.text,
        created_at=datetime.now(timezone.utc),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    comment.author = current_user
    background_tasks.add_task(notify_new_comment, db, campaign, body.text, current_user)
    return comment
