import numpy as np
import pandas as pd

from sleep_staging.training import (
    MlflowConfig,
    SupervisedDataset,
    compare_evaluations,
    create_random_forest_classifier,
    grouped_grid_search,
    split_by_subject,
    train_and_evaluate,
)


def make_dataset() -> SupervisedDataset:
    rng = np.random.default_rng(42)
    subjects = np.repeat([f"S{i:02d}" for i in range(6)], 10)
    labels = np.tile(["W", "N1", "N2", "N3", "REM"], 12)
    features = pd.DataFrame(rng.normal(size=(60, 8)))
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
