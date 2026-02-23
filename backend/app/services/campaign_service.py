"""
Campaign service: status transition validation, file handling, asset management.
"""
import re
import unicodedata
from datetime import datetime
from typing import Optional, BinaryIO

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_file import CampaignFile
from app.models.campaign_asset import CampaignAsset
from app.models.campaign_move_log import CampaignMoveLog
from app.models.user import User, UserRole
from app.storage import storage
from app.services.schedule_service import validate_email_slot

PDF_MAX_BYTES = 20 * 1024 * 1024  # 20 MB
ASSET_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_ASSET_MIME = {"image/png", "image/jpeg", "image/webp", "image/gif"}

# Statuses that require a valid send_at and pass slot validation
SLOT_REQUIRED_STATUSES = {CampaignStatus.scheduled, CampaignStatus.approved}

# --------------------------------------------------------------------------- #
# Transition matrix
# --------------------------------------------------------------------------- #
# Format: {(from_status, role): set_of_allowed_to_statuses}
TRANSITIONS: dict[tuple[CampaignStatus, UserRole], set[CampaignStatus]] = {
    # REQUESTER
    (CampaignStatus.changes_needed, UserRole.requester): {CampaignStatus.submitted},
    # MARKETING
    (CampaignStatus.submitted, UserRole.marketing): {
        CampaignStatus.in_review,
        CampaignStatus.changes_needed,
        CampaignStatus.scheduled,
        CampaignStatus.approved,
        CampaignStatus.rejected,
    },
    (CampaignStatus.in_review, UserRole.marketing): {
        CampaignStatus.changes_needed,
        CampaignStatus.scheduled,
        CampaignStatus.approved,
        CampaignStatus.rejected,
    },
    (CampaignStatus.changes_needed, UserRole.marketing): {
        CampaignStatus.in_review,
        CampaignStatus.rejected,
    },
    (CampaignStatus.scheduled, UserRole.marketing): {
        CampaignStatus.approved,
        CampaignStatus.rejected,
        CampaignStatus.sent,
    },
    (CampaignStatus.approved, UserRole.marketing): {
        CampaignStatus.scheduled,
        CampaignStatus.rejected,
        CampaignStatus.sent,
    },
}


def assert_transition(
    current: CampaignStatus,
    target: CampaignStatus,
    role: UserRole,
) -> None:
    allowed = TRANSITIONS.get((current, role), set())
    if target not in allowed:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_TRANSITION",
                "message": (
                    f"Statuswechsel von '{current}' nach '{target}' "
                    f"ist für Rolle '{role}' nicht erlaubt."
                ),
            },
        )


# Statuses in which Marketing may still modify files/assets.
MARKETING_EDITABLE_STATUSES = {
    CampaignStatus.submitted,
    CampaignStatus.in_review,
    CampaignStatus.changes_needed,
    CampaignStatus.scheduled,
    CampaignStatus.approved,
}

# Statuses in which a Requester may still modify files/assets.
# Locked at 'approved': once approved the campaign is fixed.
REQUESTER_EDITABLE_STATUSES = {
    CampaignStatus.submitted,
    CampaignStatus.in_review,
    CampaignStatus.changes_needed,
    CampaignStatus.scheduled,
}

# --------------------------------------------------------------------------- #
# Asset permissions
# --------------------------------------------------------------------------- #
def assert_asset_upload_allowed(status: CampaignStatus, role: UserRole) -> None:
    allowed = MARKETING_EDITABLE_STATUSES if role == UserRole.marketing else REQUESTER_EDITABLE_STATUSES
    if status not in allowed:
        raise HTTPException(
            status_code=403,
            detail="Dateien können in diesem Status nicht mehr geändert werden.",
        )


# --------------------------------------------------------------------------- #
# File helpers
# --------------------------------------------------------------------------- #
def _sanitize_filename(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^\w\.\-]", "_", name)
    name = re.sub(r"_+", "_", name)
    return name[:200]


def save_pdf(
    db: Session,
    campaign: Campaign,
    file: UploadFile,
    uploader: User,
) -> CampaignFile:
    """Validate and persist a new PDF version for the campaign."""
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        # Re-check by filename extension as a fallback
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(status_code=422, detail="Nur PDF-Dateien erlaubt.")

    raw = file.file.read()
    if len(raw) > PDF_MAX_BYTES:
        raise HTTPException(status_code=413, detail="PDF darf maximal 20 MB groß sein.")
    if len(raw) == 0:
        raise HTTPException(status_code=422, detail="Leere Datei hochgeladen.")

    # Determine next version number
    existing_versions = [f.version for f in campaign.files]
    version = (max(existing_versions) + 1) if existing_versions else 1
    rel_path = f"campaigns/{campaign.id}/pdf/v{version}.pdf"

    import io
    storage.save(rel_path, io.BytesIO(raw))

    cf = CampaignFile(
        campaign_id=campaign.id,
        version=version,
        original_filename=file.filename or "upload.pdf",
        storage_path=rel_path,
        file_size=len(raw),
        uploaded_by_id=uploader.id,
        uploaded_at=datetime.utcnow(),
    )
    db.add(cf)
    db.flush()
    return cf


def save_asset(
    db: Session,
    campaign: Campaign,
    file: UploadFile,
    uploader: User,
) -> CampaignAsset:
    """Validate and persist a single asset for the campaign."""
    assert_asset_upload_allowed(campaign.status, uploader.role)

    mime = file.content_type or ""
    if mime not in ALLOWED_ASSET_MIME:
        raise HTTPException(
            status_code=422,
            detail=f"Nicht erlaubter Dateityp: {mime}. Erlaubt: {', '.join(ALLOWED_ASSET_MIME)}",
        )

    raw = file.file.read()
    if len(raw) > ASSET_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Asset darf maximal 10 MB groß sein.")
    if len(raw) == 0:
        raise HTTPException(status_code=422, detail="Leere Datei hochgeladen.")

    sanitized = _sanitize_filename(file.filename or "asset")

    # Insert to get an ID first, then build the path
    asset = CampaignAsset(
        campaign_id=campaign.id,
        original_filename=file.filename or "asset",
        sanitized_filename=sanitized,
        storage_path="",  # updated below
        mime_type=mime,
        file_size=len(raw),
        uploaded_by_id=uploader.id,
        uploaded_at=datetime.utcnow(),
    )
    db.add(asset)
    db.flush()  # get asset.id

    rel_path = f"campaigns/{campaign.id}/assets/{asset.id}-{sanitized}"
    import io
    storage.save(rel_path, io.BytesIO(raw))
    asset.storage_path = rel_path
    db.flush()
    return asset


def apply_status_transition(
    db: Session,
    campaign: Campaign,
    new_status: CampaignStatus,
    actor: User,
    send_at: Optional[datetime] = None,
    reason: Optional[str] = None,
) -> Campaign:
    """
    Apply a validated status transition, including send_at slot validation
    where required.  Records move_log for downgrade approved→scheduled.
    """
    assert_transition(campaign.status, new_status, actor.role)

    # Slot validation when transitioning to a status that pins a send date
    if campaign.channel == "email" and new_status in SLOT_REQUIRED_STATUSES:
        effective_send_at = send_at or campaign.send_at
        if effective_send_at is None:
            raise HTTPException(
                status_code=422,
                detail="send_at muss angegeben werden wenn der Status einen Termin erfordert.",
            )
        validate_email_slot(db, effective_send_at, campaign_id=campaign.id)
        campaign.send_at = effective_send_at

    # For downgrade approved → scheduled, log it
    if (
        campaign.status == CampaignStatus.approved
        and new_status == CampaignStatus.scheduled
    ):
        if not reason:
            raise HTTPException(
                status_code=422,
                detail="Begründung erforderlich für Downgrade approved → scheduled.",
            )
        log = CampaignMoveLog(
            campaign_id=campaign.id,
            moved_by_id=actor.id,
            old_send_at=campaign.send_at,
            new_send_at=send_at or campaign.send_at,
            reason=reason,
        )
        db.add(log)

    # For approved → rejected, reason recommended but not mandatory per spec
    campaign.status = new_status
    campaign.updated_at = datetime.utcnow()
    db.flush()
    return campaign
