"""Orquestación de una inferencia sin lógica científica duplicada."""

from __future__ import annotations

from typing import Protocol
from uuid import uuid4

import numpy as np

from sleep_staging.inference import ModelManifest, PredictionResult

from sleep_api.core.exceptions import ModelUnavailableError
from sleep_api.infrastructure.uploads import LocalUploadRepository
from sleep_api.schemas.predictions import (
    EpochPrediction,
    InferenceResponse,
    SleepSummary,
)


class Predictor(Protocol):
    model_version: str
    manifest: ModelManifest

    def predict_edf(self, path: str) -> PredictionResult: ...


class PredictionService:
    def __init__(
        self,
        uploads: LocalUploadRepository,
        predictor: Predictor | None,
        model_error: str | None = None,
    ) -> None:
        self.uploads = uploads
        self.predictor = predictor
        self.model_error = model_error

    def predict(self, upload_id: str) -> InferenceResponse:
        if self.predictor is None:
            detail = self.model_error or "El modelo no está cargado"
            raise ModelUnavailableError(detail)

        stored = self.uploads.get(upload_id)
        result = self.predictor.predict_edf(str(stored.file_path))
        classes = tuple(self.predictor.manifest.classes)
        epochs = []
        duration_by_stage = {stage: 0.0 for stage in classes}

        for index, stage in enumerate(result.stages):
            duration = float(result.duration_seconds[index])
            row = result.probabilities[index]
            duration_by_stage[stage] += duration
            epochs.append(
                EpochPrediction(
                    epoch_index=index,
                    onset_seconds=float(result.onset_seconds[index]),
                    duration_seconds=duration,
                    stage=stage,
                    confidence=float(np.max(row)),
                    probabilities={
                        label: float(probability)
                        for label, probability in zip(classes, row, strict=True)
                    },
                )
            )

        total_duration = float(sum(duration_by_stage.values()))
        percentages = {
            stage: (duration / total_duration * 100.0 if total_duration else 0.0)
            for stage, duration in duration_by_stage.items()
        }
        epoch_seconds = (
            float(result.duration_seconds[0]) if len(result.duration_seconds) else 0.0
        )
        return InferenceResponse(
            prediction_id=str(uuid4()),
            upload_id=stored.upload_id,
            patient_name=stored.patient_name,
            model_version=self.predictor.model_version,
            preprocessing_version="sleep-staging-0.1.0",
            channels=list(result.channels),
            sfreq=result.sfreq,
            epoch_seconds=epoch_seconds,
            epochs=epochs,
            summary=SleepSummary(
                total_epochs=len(epochs),
                total_duration_seconds=total_duration,
                duration_by_stage_seconds=duration_by_stage,
                percentage_by_stage=percentages,
            ),
        )
