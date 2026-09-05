from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sleep_staging import PreprocessingConfig
from sleep_staging.inference import PredictionResult

from sleep_api.core.config import Settings
from sleep_api.main import create_app


class FakePredictor:
    model_version = "test-v1"
    manifest = SimpleNamespace(
        classes=("N1", "N2", "N3", "REM", "W"),
        artifact_version=1,
        model_type="Fake",
        feature_columns=("a", "b"),
        preprocessing=PreprocessingConfig(),
    )

    def predict_edf(self, path: str) -> PredictionResult:
        assert Path(path).is_file()
        probabilities = np.asarray(
            [
                [0.05, 0.10, 0.05, 0.10, 0.70],
                [0.10, 0.60, 0.10, 0.15, 0.05],
            ]
        )
        return PredictionResult(
            stages=("W", "N2"),
            probabilities=probabilities,
            onset_seconds=np.asarray([0.0, 30.0]),
            duration_seconds=np.asarray([30.0, 30.0]),
            sfreq=100.0,
            channels=("EEG Fpz-Cz", "EEG Pz-Oz"),
        )


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        model_dir=tmp_path / "missing-model",
        upload_dir=tmp_path / "uploads",
        max_upload_bytes=1024,
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        app.state.predictor = FakePredictor()
        app.state.model_error = None
        yield test_client

