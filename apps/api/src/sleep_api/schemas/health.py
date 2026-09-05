from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    api_version: str
    model_ready: bool
    model_version: str | None = None
    detail: str | None = None


class ModelInfoResponse(BaseModel):
    model_ready: bool
    artifact_version: int | None = None
    model_type: str | None = None
    classes: list[str] = Field(default_factory=list)
    feature_count: int | None = None
    channels: list[str] = Field(default_factory=list)
    expected_sfreq: float | None = None
    epoch_seconds: float | None = None
