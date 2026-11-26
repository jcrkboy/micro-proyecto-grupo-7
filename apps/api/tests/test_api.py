import asyncio
import json
import os
from concurrent.futures import CancelledError
from io import BytesIO
from threading import Event
from time import monotonic, sleep
from uuid import uuid4

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

from sleep_api.api.routes.predictions import _StageTimes, infer_with_progress
from sleep_api.core.config import Settings
from sleep_api.main import create_app
from sleep_api.schemas.predictions import InferenceRequest
from sleep_api.services.prediction_service import PredictionService


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
    root = client.app.state.settings.upload_dir
    assert not (root / f"{upload_id}.edf").exists()
    assert not (root / f"{upload_id}.json").exists()
    assert client.post("/inferencia", json={"upload_id": upload_id}).status_code == 404


def test_upload_rejects_non_edf_file(client: TestClient) -> None:
    response = client.post(
        "/api/v1/uploads",
        data={"patient_name": "Persona"},
        files={"file": ("notes.txt", b"not edf", "text/plain")},
    )

    assert response.status_code == 422
    assert "extensión .edf" in response.json()["detail"]


def test_progress_stream_releases_files_on_success_and_failure(client, monkeypatch):
    root = client.app.state.settings.upload_dir
    predictor = client.app.state.predictor
    original_predict = predictor.predict_edf

    def predict(path, channels, *, on_progress, check_cancelled):
        on_progress("processing")
        check_cancelled()
        if channels:
            raise ValueError("Selección inválida")
        return original_predict(path, channels)

    monkeypatch.setattr(predictor, "predict_edf", predict)
    for channels, terminal in [(None, "result"), (["inválido"], "error")]:
        upload_id = upload_test_file(client)
        response = client.post("/api/v1/inferencia/progreso", json={"upload_id": upload_id, "channels": channels})
        assert [json.loads(line)["type"] for line in response.text.splitlines()] == ["progress", terminal]
        assert list(root.glob(f"{upload_id}.*")) == []


def test_queue_protects_expired_edf_and_cancellation_releases_it(client):
    state = client.app.state
    service = PredictionService(state.upload_repository, state.predictor, state.inference_slot)
    upload_id = upload_test_file(client)
    root = state.settings.upload_dir
    files = list(root.glob(f"{upload_id}.*"))
    assert len(files) == 2

    async def check_queue():
        async with state.inference_slot:
            task = asyncio.create_task(service.predict(upload_id))
            await asyncio.sleep(0)  # La solicitud alcanzó el punto de espera del modelo.
            for path in files:
                os.utime(path, (1, 1))
            state.upload_repository.remove_expired()
            assert all(path.exists() for path in files)
            duplicate = await asyncio.to_thread(client.post, "/inferencia", json={"upload_id": upload_id})
            assert duplicate.status_code == 409
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        assert not any(path.exists() for path in files)

    client.portal.call(check_queue)


def test_cleanup_on_start_and_upload_preserves_unrelated_and_recent_files(tmp_path):
    def old_file(name):
        path = tmp_path / name
        path.write_bytes(b"test")
        os.utime(path, (1, 1))
        return path

    def wait_removed(path):
        deadline = monotonic() + 5
        while path.exists() and monotonic() < deadline:
            sleep(0.01)
        assert not path.exists()

    orphan = old_file(f"{uuid4()}.part")
    unrelated = old_file("otra-grabacion.edf")
    app = create_app(Settings(model_dir=tmp_path / "missing", upload_dir=tmp_path))
    with TestClient(app) as client:
        wait_removed(orphan)
        abandoned_id = str(uuid4())
        edf = old_file(f"{abandoned_id}.edf")
        metadata = old_file(f"{abandoned_id}.json")
        fresh_id = upload_test_file(client)
        wait_removed(edf)
        wait_removed(metadata)
        assert unrelated.is_file()
        assert (tmp_path / f"{fresh_id}.edf").is_file()
        assert (tmp_path / f"{fresh_id}.json").is_file()


def test_abandoned_upload_expires_without_more_requests(tmp_path):
    app = create_app(Settings(model_dir=tmp_path / "missing", upload_dir=tmp_path, upload_ttl_seconds=1))
    with TestClient(app) as client:
        upload_id = upload_test_file(client)
        deadline = monotonic() + 5
        while list(tmp_path.glob(f"{upload_id}.*")) and monotonic() < deadline:
            sleep(0.05)
        assert list(tmp_path.glob(f"{upload_id}.*")) == []


def test_upload_rejects_invalid_edf_header(client: TestClient) -> None:
    response = client.post(
        "/api/v1/uploads",
        data={"patient_name": "Persona"},
        files={"file": ("fake.edf", b"not really an EDF", "application/octet-stream")},
    )

    assert response.status_code == 422
    assert "cabecera EDF" in response.json()["detail"]
    assert list(client.app.state.settings.upload_dir.iterdir()) == []


def test_slow_upload_is_protected_until_client_cancels(client, monkeypatch):
    repo = client.app.state.upload_repository
    upload = UploadFile(file=BytesIO(), filename="lento.edf")

    async def interrupt_read(size):
        part, = repo.root.glob("*.part")
        os.utime(part, (1, 1))
        await asyncio.to_thread(repo.remove_expired)
        assert part.is_file()
        raise asyncio.CancelledError()

    monkeypatch.setattr(upload, "read", interrupt_read)

    async def check_cleanup():
        with pytest.raises(asyncio.CancelledError):
            await repo.save("Prueba", upload)
        assert list(repo.root.iterdir()) == []

    client.portal.call(check_cleanup)


def test_inference_returns_404_for_unknown_upload(client: TestClient) -> None:
    response = client.post(
        "/inferencia", json={"upload_id": "00000000-0000-0000-0000-000000000000"}
    )

    assert response.status_code == 404


def test_disconnecting_progress_stream_stops_server_work(client, monkeypatch):
    stopped = Event()
    state = client.app.state
    upload_id = upload_test_file(client)
    edf = state.settings.upload_dir / f"{upload_id}.edf"

    def run(path, channels, *, on_progress, check_cancelled):
        on_progress("processing")
        for _ in range(100):
            try:
                check_cancelled()
            except CancelledError:
                assert edf.is_file()
                stopped.set()
                raise
            stopped.wait(0.02)
        raise AssertionError("El modelo continuó después de la desconexión")

    monkeypatch.setattr(state.predictor, "predict_edf", run)
    service = PredictionService(state.upload_repository, state.predictor, state.inference_slot)

    async def disconnect():
        response = await infer_with_progress(InferenceRequest(upload_id=upload_id), service)
        stream = response.body_iterator
        first = json.loads(await asyncio.wait_for(anext(stream), timeout=5))
        assert first["stage"] == "processing"
        assert first["elapsed_ms"] >= 0
        await stream.aclose()
        assert stopped.is_set()

    client.portal.call(disconnect)
    assert not list(state.settings.upload_dir.glob(f"{upload_id}.*"))


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
