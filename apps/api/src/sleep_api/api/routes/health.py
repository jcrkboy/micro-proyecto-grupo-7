from fastapi import APIRouter, Request, Response, status

from sleep_api.schemas.health import HealthResponse, ModelInfoResponse


router = APIRouter(tags=["operación"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request, response: Response) -> HealthResponse:
    predictor = request.app.state.predictor
    error = request.app.state.model_error
    if predictor is None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="ok" if predictor is not None else "degraded",
        api_version=request.app.state.settings.api_version,
        model_ready=predictor is not None,
        model_version=predictor.model_version if predictor is not None else None,
        detail=error,
    )


@router.get("/model", response_model=ModelInfoResponse)
def model_info(request: Request) -> ModelInfoResponse:
    predictor = request.app.state.predictor
    if predictor is None:
        return ModelInfoResponse(model_ready=False)
    manifest = predictor.manifest
    config = manifest.preprocessing
    return ModelInfoResponse(
        model_ready=True,
        artifact_version=manifest.artifact_version,
        model_type=manifest.model_type,
        classes=list(manifest.classes),
        feature_count=len(manifest.feature_columns),
        channels=list(config.channels),
        expected_sfreq=config.expected_sfreq,
        epoch_seconds=config.epoch_seconds,
    )
