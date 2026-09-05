"""Prueba local real; se omite en CI mientras el bundle no esté versionado."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sleep_api.core.config import Settings
from sleep_api.main import create_app


REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = REPO_ROOT / "data" / "models" / "sleep_staging_lightgbm_eeg_v2"
SAMPLE_EDF = Path(__file__).parent / "fixtures" / "sample_eeg_60s.edf"


@pytest.mark.skipif(
    not (MODEL_DIR / "model.txt").is_file(),
    reason="El bundle real aún no está disponible en CI",
)
def test_real_model_predicts_two_epochs(tmp_path) -> None:
    app = create_app(
        Settings(model_dir=MODEL_DIR, upload_dir=tmp_path / "uploads")
    )

    with TestClient(app) as client, SAMPLE_EDF.open("rb") as stream:
        health = client.get("/health")
        uploaded = client.post(
            "/api/v1/uploads",
            data={"patient_name": "Paciente sintético"},
            files={"file": (SAMPLE_EDF.name, stream, "application/octet-stream")},
        )
        inferred = client.post(
            "/api/v1/inferencia",
            json={"upload_id": uploaded.json()["upload_id"]},
        )

    assert health.json()["model_ready"] is True
    assert uploaded.status_code == 201
    assert inferred.status_code == 200
    body = inferred.json()
    assert body["summary"]["total_epochs"] == 2
    assert body["summary"]["total_duration_seconds"] == 60.0
    assert set(body["epochs"][0]["probabilities"]) == {"N1", "N2", "N3", "REM", "W"}

