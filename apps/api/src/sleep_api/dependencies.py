from fastapi import Request

from sleep_api.infrastructure.uploads import LocalUploadRepository
from sleep_api.services.prediction_service import PredictionService


def get_upload_repository(request: Request) -> LocalUploadRepository:
    return request.app.state.upload_repository


def get_prediction_service(request: Request) -> PredictionService:
    return PredictionService(
        uploads=request.app.state.upload_repository,
        predictor=request.app.state.predictor,
        inference_slot=request.app.state.inference_slot,
        model_error=request.app.state.model_error,
    )

