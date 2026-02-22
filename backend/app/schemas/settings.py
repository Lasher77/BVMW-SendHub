from pydantic import BaseModel, Field


class SettingsOut(BaseModel):
    id: int
    min_gap_days: int

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    min_gap_days: int = Field(..., ge=1, le=365)
