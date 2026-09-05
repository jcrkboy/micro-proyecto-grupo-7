from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from sleep_api.core.exceptions import ModelUnavailableError, UploadNotFoundError
from sleep_api.dependencies import get_prediction_service
from sleep_api.schemas.predictions import InferenceRequest, InferenceResponse
from sleep_api.services.prediction_service import PredictionService


router = APIRouter(tags=["inferencia"])


@router.post("/inferencia", response_model=InferenceResponse)
def infer(
    payload: InferenceRequest,
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> InferenceResponse:
    try:
        return service.predict(payload.upload_id)
    except UploadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

