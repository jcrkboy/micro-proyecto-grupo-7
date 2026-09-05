"""Recursos que viven durante todo el proceso FastAPI."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from sleep_staging.inference import SleepStagePredictor

from sleep_api.infrastructure.uploads import LocalUploadRepository


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = app.state.settings
    app.state.upload_repository = LocalUploadRepository(
        root=settings.upload_dir,
        max_bytes=settings.max_upload_bytes,
    )
    app.state.predictor = None
    app.state.model_error = None
    try:
        app.state.predictor = SleepStagePredictor(settings.model_dir)
    except Exception as exc:  # La API queda viva para exponer health degradado.
        app.state.model_error = str(exc)
        logger.exception("No fue posible cargar el bundle de inferencia")
    yield

