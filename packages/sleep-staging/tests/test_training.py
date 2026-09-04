from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from sleep_staging import PreprocessingConfig, PreprocessingPipeline
from sleep_staging.datasets import SleepEdfRecord
from sleep_staging.training import (
    MlflowConfig,
    SupervisedDataset,
    compare_evaluations,
    create_random_forest_classifier,
    grouped_grid_search,
    load_or_build_supervised_dataset,
    split_by_subject,
    train_and_evaluate,
)
from sleep_staging.training.runner import _skops_trusted_types_for


def make_dataset() -> SupervisedDataset:
    rng = np.random.default_rng(42)
    subjects = np.repeat([f"S{i:02d}" for i in range(6)], 10)
    labels = np.tile(["W", "N1", "N2", "N3", "REM"], 12)
    features = pd.DataFrame(
        rng.normal(size=(60, 8)),
        columns=[f"feature_{index}" for index in range(8)],
    )
    metadata = pd.DataFrame(
        {
            "subject_id": subjects,
            "record_id": [f"R{i:02d}" for i in range(60)],
            "night": np.tile([1, 2], 30),
        }
    )
    return SupervisedDataset(features, pd.Series(labels, name="stage"), metadata)


def test_split_by_subject_prevents_subject_leakage() -> None:
    split = split_by_subject(make_dataset(), validation_size=0.33, random_state=42)

    assert set(split.train_subjects).isdisjoint(split.validation_subjects)
    assert len(split.X_train) + len(split.X_validation) == 60
    assert len(split.y_train) == len(split.X_train)
    assert len(split.y_validation) == len(split.X_validation)


def test_supervised_dataset_cache_is_reused(tmp_path) -> None:
    psg_path = tmp_path / "ST7011J0-PSG.edf"
    hypnogram_path = tmp_path / "ST7011JM-Hypnogram.edf"
    psg_path.write_bytes(b"psg")
    hypnogram_path.write_bytes(b"hypnogram")
    records = [
        SleepEdfRecord(
            psg_path=psg_path,
            hypnogram_path=hypnogram_path,
            record_id="ST7011",
            subject_id="S01",
            night=1,
        )
    ]
    pipeline = PreprocessingPipeline(PreprocessingConfig())
    expected = make_dataset()

    with patch(
        "sleep_staging.training.cache.build_supervised_dataset",
        return_value=expected,
    ) as builder:
        first = load_or_build_supervised_dataset(
            records, pipeline, tmp_path / "processed", verbose=False
        )
        second = load_or_build_supervised_dataset(
            records, pipeline, tmp_path / "processed", verbose=False
        )

    builder.assert_called_once()
    pd.testing.assert_frame_equal(first.features, second.features)
    pd.testing.assert_series_equal(first.labels, second.labels)
    pd.testing.assert_frame_equal(first.metadata, second.metadata)
    assert len(list((tmp_path / "processed").glob("*/manifest.json"))) == 1


def test_training_runs_without_mlflow_when_disabled() -> None:
    split = split_by_subject(make_dataset(), validation_size=0.33, random_state=42)
    model = create_random_forest_classifier(n_estimators=10, random_state=42)

    evaluation = train_and_evaluate(
        model,
        split,
        model_name="Random Forest test",
        mlflow_config=MlflowConfig(enabled=False),
    )

    comparison = compare_evaluations(evaluation)
    assert set(evaluation.metrics) == {"accuracy", "kappa", "f1_macro"}
    assert evaluation.confusion.shape == (5, 5)
    assert comparison.index.tolist() == ["Random Forest test"]


def test_lightgbm_types_are_trusted_for_skops_serialization() -> None:
    lightgbm_model_type = type(
        "LGBMClassifier",
        (),
        {"__module__": "lightgbm.sklearn"},
    )

    assert _skops_trusted_types_for(lightgbm_model_type()) == [
        "collections.OrderedDict",
        "lightgbm.basic.Booster",
        "lightgbm.sklearn.LGBMClassifier",
    ]
    assert _skops_trusted_types_for(object()) is None


def test_mlflow_failure_does_not_discard_training_result(tmp_path) -> None:
    mlflow_sklearn = pytest.importorskip("mlflow.sklearn")
    split = split_by_subject(make_dataset(), validation_size=0.33, random_state=42)
    model = create_random_forest_classifier(n_estimators=5, random_state=42)
    tracking_uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"

    with (
        patch.object(
            mlflow_sklearn,
            "log_model",
            side_effect=RuntimeError("artifact store unavailable"),
        ),
        pytest.warns(RuntimeWarning, match="resultados se conservan"),
    ):
        evaluation = train_and_evaluate(
            model,
            split,
            model_name="MLflow failure test",
            mlflow_config=MlflowConfig(enabled=True, tracking_uri=tracking_uri),
        )

    assert evaluation.model_name == "MLflow failure test"


def test_grouped_grid_search_uses_training_and_returns_best_model() -> None:
    split = split_by_subject(make_dataset(), validation_size=0.33, random_state=42)
    model = create_random_forest_classifier(
        n_estimators=5,
        n_jobs=1,
        random_state=42,
    )

    result = grouped_grid_search(
        model,
        {"max_depth": [2, None], "min_samples_leaf": [1]},
        split,
        model_name="Random Forest grid test",
        n_splits=2,
        n_jobs=1,
        verbose=0,
    )

    assert result.best_parameters["max_depth"] in {2, None}
    assert len(result.cv_results) == 2
    assert result.refit_metric == "f1_macro"
    assert result.validation_evaluation.model_name == "Random Forest grid test"
