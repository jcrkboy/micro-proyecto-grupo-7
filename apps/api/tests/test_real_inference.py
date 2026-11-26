"""Inferencia con el modelo distribuido en Git y un EDF sintético de 60 s."""

from pathlib import Path
from threading import Barrier

import edfio
import numpy as np
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
        upload_id = missing.json()["upload_id"]
        eeg_only = client.post("/inferencia", json={"upload_id": upload_id})
        assert eeg_only.status_code == 200, eeg_only.text
        assert eeg_only.json()["channels"] == ["EEG Fpz-Cz", "EEG Pz-Oz"]
        for channels in ([], ["EMG submental"], ["Marker"], ["EEG Pz-Oz", "EEG Pz-Oz"]):
            invalid = client.post("/inferencia", json={"upload_id": upload_id, "channels": channels})
            assert invalid.status_code == 422
        no_eeg = client.post("/inferencia", json={
            "upload_id": uploaded.json()["upload_id"], "channels": ["EOG horizontal"],
        })
        assert no_eeg.status_code == 422
        assert "al menos un EEG" in no_eeg.json()["detail"]

    assert uploaded.status_code == 201
    assert inferred.status_code == 200
    body = inferred.json()
    assert body["summary"]["total_epochs"] == 2
    assert body["summary"]["total_duration_seconds"] == 60.0
    assert set(body["epochs"][0]["probabilities"]) == {"N1", "N2", "N3", "REM", "W"}
    for epoch in body["epochs"]:
        assert sum(epoch["probabilities"].values()) == pytest.approx(1.0)
        assert epoch["confidence"] == epoch["probabilities"][epoch["stage"]]


def test_channel_masks_keep_model_slots_and_ignore_unselected_signals(tmp_path, monkeypatch):
    from sleep_staging.inference import mixed

    app = create_app(Settings(_env_file=None, upload_dir=tmp_path / "uploads"))
    with TestClient(app):
        predictor = app.state.predictor
        channels = predictor.channels
        originals = edfio.read_edf(SAMPLE_EDF).signals
        path = tmp_path / "cuatro.edf"
        def write_edf(rate):
            emg = edfio.EdfSignal(
                np.cos(np.arange(60 * rate)), rate, label=channels[3], physical_dimension="uV",
            )
            edfio.Edf([*originals, emg]).write(path)

        write_edf(100)
        # Inspeccionar los tensores justo antes de que entren a los dos modelos.
        inputs = {}
        def capture_dart(frame, **kwargs):
            inputs["dart"] = frame
            return np.full((len(frame), 5), 0.2)

        def capture_crnn(model, features, offsets, classes):
            inputs["crnn"] = features
            return np.full((len(features), classes), 1 / classes)

        monkeypatch.setattr(predictor.dart, "predict", capture_dart)
        monkeypatch.setattr(mixed, "crnn_probabilities", capture_crnn)
        predictor.predict_edf(path)
        full_dart, full_crnn = inputs["dart"], inputs["crnn"]
        prefixes = ("FpzCz_", "PzOz_", "EOG_horizontal_", "EMG_submental_")
        for mask in range(1, 16):
            if not mask & 3:
                continue
            selected = [ch for i, ch in enumerate(channels) if mask & (1 << i)]
            result = predictor.predict_edf(path, channels=selected[::-1])
            assert list(result.channels) == selected
            assert list(inputs["dart"].columns) == list(full_dart.columns)
            for i, (ch, prefix) in enumerate(zip(channels, prefixes)):
                columns = full_dart.columns.str.startswith(prefix)
                assert columns.any()
                np.testing.assert_allclose(
                    inputs["dart"].loc[:, columns], full_dart.loc[:, columns] if ch in selected else 0,
                )
                np.testing.assert_allclose(
                    inputs["crnn"][:, :, i::4], full_crnn[:, :, i::4] if ch in selected else 0,
                    atol=1e-5,
                )
            inter = full_dart.columns.str.startswith("inter_ratio_")
            assert inter.any()
            np.testing.assert_allclose(
                inputs["dart"].loc[:, inter], full_dart.loc[:, inter] if mask & 3 == 3 else 0,
            )

        write_edf(1)
        assert predictor.predict_edf(path).channels == channels
        assert inputs["dart"].filter(like="EMG_submental_").isna().all().all()
        assert np.any(inputs["crnn"][:, :, 3::4])
        write_edf(10)
        with pytest.raises(ValueError, match="Frecuencia incompatible"):
            predictor.predict_edf(path, channels=[channels[0], channels[3]])
        assert predictor.predict_edf(path).channels == channels[:3]

