from io import BytesIO

from fastapi.testclient import TestClient

from sleep_api.core.config import Settings
from sleep_api.main import create_app


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
