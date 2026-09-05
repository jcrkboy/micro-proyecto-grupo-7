from pydantic import BaseModel, Field


class InferenceRequest(BaseModel):
    upload_id: str = Field(min_length=36, max_length=36)


class EpochPrediction(BaseModel):
    epoch_index: int
    onset_seconds: float
    duration_seconds: float
    stage: str
    confidence: float
    probabilities: dict[str, float]


class SleepSummary(BaseModel):
    total_epochs: int
    total_duration_seconds: float
    duration_by_stage_seconds: dict[str, float]
    percentage_by_stage: dict[str, float]


class InferenceResponse(BaseModel):
    prediction_id: str
    upload_id: str
    patient_name: str
    model_version: str
    preprocessing_version: str
    channels: list[str]
    sfreq: float
    epoch_seconds: float
    epochs: list[EpochPrediction]
    summary: SleepSummary
    disclaimer: str = (
        "Resultado preliminar para apoyo y revisión profesional; no constituye diagnóstico."
    )
