import json

import pytest

from sleep_staging.inference import load_manifest


def test_load_manifest_recreates_preprocessing_config(tmp_path) -> None:
    payload = {
        "artifact_version": 1,
        "model_type": "LightGBM Booster",
        "model_file": "model.txt",
        "classes": ["N1", "N2", "N3", "REM", "W"],
        "feature_columns": ["feature_a", "feature_b"],
        "preprocessing": {
            "channels": ["EEG Fpz-Cz", "EEG Pz-Oz"],
            "rolling_windows": [3, 5, 11],
        },
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    manifest = load_manifest(manifest_path)

    assert manifest.preprocessing.channels == ("EEG Fpz-Cz", "EEG Pz-Oz")
    assert manifest.preprocessing.rolling_windows == (3, 5, 11)
    assert manifest.classes[-1] == "W"


def test_load_manifest_rejects_duplicate_features(tmp_path) -> None:
    payload = {
        "artifact_version": 1,
        "model_type": "LightGBM Booster",
        "model_file": "model.txt",
        "classes": ["W"],
        "feature_columns": ["same", "same"],
        "preprocessing": {},
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="features"):
        load_manifest(manifest_path)
