import asyncio
import json
import logging
from concurrent.futures import CancelledError
from threading import Event
from time import monotonic
from typing import Annotated

from anyio import CancelScope
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from sleep_api.core.exceptions import ModelUnavailableError, UploadInUseError, UploadNotFoundError
from sleep_api.dependencies import get_prediction_service
from sleep_api.schemas.predictions import InferenceRequest, InferenceResponse
from sleep_api.services.prediction_service import PredictionService


router = APIRouter(tags=["inferencia"])


class _StageTimes:
    """Tiempo de pared con al menos una rama activa en cada etapa."""

    _active_stages = {
        "processing_ms": {"processing", "overlap"},
        "inference_ms": {"inferring", "overlap"},
        "overlap_ms": {"overlap"},
    }

    def __init__(self):
        self.stage = "waiting"
        self.last_ms = 0
        self.totals = {"processing_ms": None, "inference_ms": None, "overlap_ms": 0}

    def advance(self, stage: str, elapsed_ms: int) -> dict:
        interval = elapsed_ms - self.last_ms
        for key, stages in self._active_stages.items():
            if self.stage in stages:
                self.totals[key] += interval
            elif stage in stages and self.totals[key] is None:
                self.totals[key] = 0
        self.stage = stage
        self.last_ms = elapsed_ms
        return self.totals.copy()


@router.post("/inferencia", response_model=InferenceResponse)
async def infer(
    payload: InferenceRequest,
    service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> InferenceResponse:
    try:
        return await service.predict(payload.upload_id, payload.channels)
    except UploadInUseError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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
        times = _StageTimes()
        messages = asyncio.Queue()
        disconnected = Event()
        work_scope = CancelScope()

        def publish(message):
            if not disconnected.is_set():
                message["elapsed_ms"] = round((monotonic() - started) * 1000)
                if message["type"] in {"progress", "result"}:
                    message["timings"] = times.advance(message.get("stage", "finalizing"), message["elapsed_ms"])
                loop.call_soon_threadsafe(messages.put_nowait, message)

        def check_cancelled():
            if disconnected.is_set():
                raise CancelledError()

        async def predict():
            try:
                with work_scope:
                    prediction = await service.predict(
                        payload.upload_id, payload.channels,
                        on_progress=lambda stage: publish({"type": "progress", "stage": stage}),
                        check_cancelled=check_cancelled,
                    )
                    publish({"type": "result", "prediction": prediction.model_dump(mode="json")})
            except CancelledError:
                logging.getLogger(__name__).info("Inferencia cancelada por el cliente")
            except (UploadInUseError, UploadNotFoundError, ModelUnavailableError, FileNotFoundError, ValueError) as exc:
                publish({"type": "error", "detail": str(exc)})
            except Exception:
                logging.getLogger(__name__).exception("Falló la inferencia con progreso")
                publish({"type": "error", "detail": "No fue posible completar el análisis."})

        worker = asyncio.create_task(predict())
        try:
            while True:
                try:
                    message = await asyncio.wait_for(messages.get(), timeout=30)
                except asyncio.TimeoutError:
                    # Espacio JSON antes del siguiente evento para mantener abierta la conexión.
                    yield " "
                    continue
                yield json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n"
                if message["type"] != "progress":
                    break
        finally:
            disconnected.set()
            work_scope.cancel()
            # La cola se cancela enseguida. Un cálculo en curso debe soltar el EDF primero.
            with CancelScope(shield=True):
                await asyncio.shield(worker)

    return StreamingResponse(
        events(), media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"},
    )

