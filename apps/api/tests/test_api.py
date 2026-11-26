import asyncio
import json
from concurrent.futures import CancelledError
from io import BytesIO
from threading import Event

from fastapi.testclient import TestClient

from sleep_api.api.routes.predictions import _StageTimes, infer_with_progress
from sleep_api.core.config import Settings
from sleep_api.main import create_app
from sleep_api.schemas.predictions import InferenceRequest


def upload_test_file(client: TestClient) -> str:
    response = client.post(
        "/api/v1/uploads",
        data={"patient_name": "Persona de prueba"},
        files={
            "file": (
                "registro.edf",
                BytesIO(b"0       " + b"synthetic EDF test payload"),
                "application/octet-stream",
            )
        },
    )
    assert response.status_code == 201
    return response.json()["upload_id"]


def test_health_reports_loaded_model(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["model_version"] == "test-v1"


def test_health_is_degraded_when_model_is_missing(tmp_path) -> None:
    app = create_app(
        Settings(
            model_dir=tmp_path / "missing-model",
            upload_dir=tmp_path / "uploads",
        )
    )

    with TestClient(app) as degraded_client:
        response = degraded_client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["model_ready"] is False


def test_upload_then_infer_returns_hypnogram_contract(client: TestClient) -> None:
    upload_id = upload_test_file(client)

    response = client.post("/api/v1/inferencia", json={"upload_id": upload_id})

    assert response.status_code == 200
    body = response.json()
    assert body["patient_name"] == "Persona de prueba"
    assert [epoch["stage"] for epoch in body["epochs"]] == ["W", "N2"]
    assert body["epochs"][1]["onset_seconds"] == 30.0
    assert body["epochs"][0]["confidence"] == 0.7
    assert body["summary"]["total_duration_seconds"] == 60.0
    assert body["summary"]["percentage_by_stage"]["W"] == 50.0


def test_upload_rejects_non_edf_file(client: TestClient) -> None:
    response = client.post(
        "/api/v1/uploads",
        data={"patient_name": "Persona"},
        files={"file": ("notes.txt", b"not edf", "text/plain")},
    )

    assert response.status_code == 422
    assert "extensión .edf" in response.json()["detail"]


def test_upload_rejects_invalid_edf_header(client: TestClient) -> None:
    response = client.post(
        "/api/v1/uploads",
        data={"patient_name": "Persona"},
        files={"file": ("fake.edf", b"not really an EDF", "application/octet-stream")},
    )

    assert response.status_code == 422
    assert "cabecera EDF" in response.json()["detail"]


def test_inference_returns_404_for_unknown_upload(client: TestClient) -> None:
    response = client.post(
        "/inferencia", json={"upload_id": "00000000-0000-0000-0000-000000000000"}
    )

    assert response.status_code == 404


def test_disconnecting_progress_stream_stops_server_work():
    resume = Event()
    stopped = Event()

    class PausedService:
        def predict(self, upload_id, channels, *, on_progress, check_cancelled):
            on_progress("processing")
            assert resume.wait(5)
            try:
                check_cancelled()
            except CancelledError:
                stopped.set()
                raise
            raise AssertionError("El modelo continuó después de la desconexión")

    async def disconnect():
        request = InferenceRequest(upload_id="00000000-0000-0000-0000-000000000000")
        response = await infer_with_progress(request, PausedService())
        stream = response.body_iterator
        try:
            first = json.loads(await asyncio.wait_for(anext(stream), timeout=5))
            assert first["stage"] == "processing"
            assert first["elapsed_ms"] >= 0
            await stream.aclose()
        finally:
            resume.set()
        assert await asyncio.to_thread(stopped.wait, 5)

    asyncio.run(disconnect())


def test_stage_times_exclude_idle_gaps_and_count_simultaneous_work_once():
    times = _StageTimes()
    times.advance("processing", 1000)
    times.advance("overlap", 1100)
    paused = times.advance("processing", 1200)
    assert paused == {"processing_ms": 200, "inference_ms": 100, "overlap_ms": 100}
    assert times.advance("inferring", 5500)["inference_ms"] == 100
    times.advance("waiting", 5600)
    times.advance("inferring", 5700)
    final = times.advance("finalizing", 5800)
    assert final == {"processing_ms": 4500, "inference_ms": 300, "overlap_ms": 100}
    assert times.advance("finalizing", 9000) == final
