"""Inferencia con el modelo distribuido en Git y un EDF sintético de 60 s."""

from pathlib import Path
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from sleep_api.core.config import Settings
from sleep_api.main import create_app


SAMPLE_EDF = Path(__file__).parent / "fixtures" / "sample_eeg_60s.edf"


def test_real_model_predicts_two_epochs(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("SLEEP_API_MODEL_DIR", raising=False)
    app = create_app(
        Settings(_env_file=None, upload_dir=tmp_path / "uploads")
    )

    with TestClient(app) as client, SAMPLE_EDF.open("rb") as stream:
        health = client.get("/health")
        assert health.json()["model_ready"] is True, health.text
        predictor = app.state.predictor
        started = Barrier(2, timeout=10)

        def wait_for_both(branch):
            def wrapped(*args):
                started.wait()
                return branch(*args)
            return wrapped

        for name in ("_tabular", "_neural"):
            monkeypatch.setattr(predictor, name, wait_for_both(getattr(predictor, name)))
        uploaded = client.post(
            "/api/v1/uploads",
            data={"patient_name": "Paciente sintético"},
            files={"file": (SAMPLE_EDF.name, stream, "application/octet-stream")},
        )
        inferred = client.post(
            "/api/v1/inferencia",
            json={"upload_id": uploaded.json()["upload_id"]},
        )
        without_eog = SAMPLE_EDF.read_bytes().replace(b"EOG horizontal", b"AUX horizontal", 1)
        missing = client.post(
            "/api/v1/uploads", data={"patient_name": "Prueba"},
            files={"file": ("solo_eeg.edf", without_eog, "application/octet-stream")},
        )
        invalid = client.post("/inferencia", json={"upload_id": missing.json()["upload_id"]})
        assert invalid.status_code == 422
        assert "EOG horizontal" in invalid.json()["detail"]

    assert uploaded.status_code == 201
    assert inferred.status_code == 200
    body = inferred.json()
    assert body["summary"]["total_epochs"] == 2
    assert body["summary"]["total_duration_seconds"] == 60.0
    assert set(body["epochs"][0]["probabilities"]) == {"N1", "N2", "N3", "REM", "W"}
    for epoch in body["epochs"]:
        assert sum(epoch["probabilities"].values()) == pytest.approx(1.0)
        assert epoch["confidence"] == epoch["probabilities"][epoch["stage"]]

