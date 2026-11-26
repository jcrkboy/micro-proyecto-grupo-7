import asyncio
import json
import logging
from concurrent.futures import CancelledError
from contextlib import suppress
from threading import Event
from time import monotonic
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

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
        return service.predict(payload.upload_id, payload.channels)
    except UploadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/inferencia/progreso", response_class=StreamingResponse)
async def infer_with_progress(
    payload: InferenceRequest,
    service: Annotated[PredictionService, Depends(get_prediction_service)],
):
    """Un evento JSON por línea, seguido de la predicción o un error terminal."""
    async def events():
        loop = asyncio.get_running_loop()
        started = monotonic()
        messages = asyncio.Queue()
        disconnected = Event()

        def publish(message):
            if not disconnected.is_set():
                message["elapsed_ms"] = round((monotonic() - started) * 1000)
                loop.call_soon_threadsafe(messages.put_nowait, message)

        def check_cancelled():
            if disconnected.is_set():
                raise CancelledError()

        def predict():
            try:
                prediction = service.predict(
                    payload.upload_id, payload.channels,
                    on_progress=lambda stage: publish({"type": "progress", "stage": stage}),
                    check_cancelled=check_cancelled,
                )
                publish({"type": "result", "prediction": prediction.model_dump(mode="json")})
            except CancelledError:
                logging.getLogger(__name__).info("Inferencia cancelada por el cliente")
            except (UploadNotFoundError, ModelUnavailableError, FileNotFoundError, ValueError) as exc:
                publish({"type": "error", "detail": str(exc)})
            except Exception:
                logging.getLogger(__name__).exception("Falló la inferencia con progreso")
                publish({"type": "error", "detail": "No fue posible completar el análisis."})

        worker = asyncio.create_task(run_in_threadpool(predict))
        try:
            while True:
                message = await messages.get()
                yield json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n"
                if message["type"] != "progress":
                    break
        finally:
            disconnected.set()
            worker.cancel()
            with suppress(asyncio.CancelledError):
                await worker

    return StreamingResponse(
        events(), media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"},
    )

