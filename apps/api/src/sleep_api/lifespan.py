"""Recursos que viven durante todo el proceso FastAPI."""

from asyncio import Lock
from contextlib import asynccontextmanager
import logging

from anyio import create_task_group
from fastapi import FastAPI
from sleep_staging.inference.mixed import MixedSleepStagePredictor

from sleep_api.infrastructure.uploads import LocalUploadRepository


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = app.state.settings
    uploads = LocalUploadRepository(
        root=settings.upload_dir,
        max_bytes=settings.max_upload_bytes,
        ttl_seconds=settings.upload_ttl_seconds,
    )
    app.state.upload_repository = uploads
    app.state.inference_slot = Lock()
    app.state.predictor = None
    app.state.model_error = None
    try:
        app.state.predictor = MixedSleepStagePredictor(settings.model_dir, require_final=True)
    except Exception as exc:  # La API queda viva para exponer health degradado.
        app.state.model_error = str(exc)
        logger.exception("No fue posible cargar el bundle de inferencia")
    async with create_task_group() as tasks:
        tasks.start_soon(uploads.run_cleanup)
        try:
            yield
        finally:
            tasks.cancel_scope.cancel()

