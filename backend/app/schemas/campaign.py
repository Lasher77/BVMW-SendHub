from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel
from app.models.campaign import CampaignStatus
from app.schemas.user import UserOut
from app.schemas.department import DepartmentOut


class CampaignFileOut(BaseModel):
    id: int
    version: int
    original_filename: str
    file_size: int
    uploaded_at: datetime
    uploaded_by: UserOut

    model_config = {"from_attributes": True}


class CampaignAssetOut(BaseModel):
    id: int
    original_filename: str
    sanitized_filename: str
    mime_type: str
    file_size: int
    is_deleted: bool
    uploaded_at: datetime
    uploaded_by: UserOut

    model_config = {"from_attributes": True}


class CampaignCommentOut(BaseModel):
    id: int
    text: str
    created_at: datetime
    author: UserOut

    model_config = {"from_attributes": True}


class CampaignMoveLogOut(BaseModel):
    id: int
    old_send_at: datetime | None
    new_send_at: datetime | None
    reason: str | None
    created_at: datetime
    moved_by: UserOut

    model_config = {"from_attributes": True}


class CampaignOut(BaseModel):
    id: int
    title: str
    channel: str
    status: CampaignStatus
    send_at: datetime | None
    created_at: datetime
    updated_at: datetime
    department: DepartmentOut
    creator: UserOut
    files: list[CampaignFileOut] = []
    assets: list[CampaignAssetOut] = []
    comments: list[CampaignCommentOut] = []
    move_logs: list[CampaignMoveLogOut] = []

    model_config = {"from_attributes": True}


class CampaignListItem(BaseModel):
    id: int
    title: str
    channel: str
    status: CampaignStatus
    send_at: datetime | None
    created_at: datetime
    department: DepartmentOut
    creator: UserOut

    model_config = {"from_attributes": True}


class CampaignStatusUpdate(BaseModel):
    status: CampaignStatus
    send_at: datetime | None = None
    reason: str | None = None


class CommentCreate(BaseModel):
    text: str
