"""Búsqueda de hiperparámetros con separación estricta por sujeto."""

from dataclasses import dataclass
import json
from typing import Any, Mapping, Sequence

import pandas as pd
from sklearn.metrics import cohen_kappa_score, f1_score, make_scorer
from sklearn.model_selection import GridSearchCV, GroupKFold

from sleep_staging.datasets import VALID_STAGES
from sleep_staging.training.dataset import TrainValidationSplit
from sleep_staging.training.evaluation import ModelEvaluation, evaluate_classifier
from sleep_staging.training.runner import (
    MlflowConfig,
    _skops_trusted_types_for,
    _warn_mlflow_failure,
)


@dataclass(frozen=True)
class GroupedGridSearchResult:
    """Mejor estimador, métricas CV y evaluación sobre el holdout intacto."""

    model_name: str
    best_estimator: Any
    best_parameters: dict[str, Any]
    best_cv_score: float
    refit_metric: str
    cv_results: pd.DataFrame
    validation_evaluation: ModelEvaluation


def _build_search(
    estimator: Any,
    parameter_grid: Mapping[str, Sequence[Any]],
    *,
    n_splits: int,
    refit_metric: str,
    n_jobs: int,
    verbose: int,
) -> GridSearchCV:
    scoring = {
        "accuracy": "accuracy",
        "f1_macro": make_scorer(
            f1_score,
            labels=list(VALID_STAGES),
            average="macro",
            zero_division=0,
        ),
        "kappa": make_scorer(cohen_kappa_score),
    }
    if refit_metric not in scoring:
        raise ValueError(f"refit_metric debe ser uno de {tuple(scoring)}")
    return GridSearchCV(
        estimator=estimator,
        param_grid=dict(parameter_grid),
        scoring=scoring,
        refit=refit_metric,
        cv=GroupKFold(n_splits=n_splits),
        n_jobs=n_jobs,
        verbose=verbose,
        return_train_score=False,
        error_score="raise",
    )


def _summarize_results(
    search: GridSearchCV,
    refit_metric: str,
) -> pd.DataFrame:
    results = pd.DataFrame(search.cv_results_)
    columns = [
        "rank_test_f1_macro",
        "mean_test_f1_macro",
        "std_test_f1_macro",
        "mean_test_kappa",
        "std_test_kappa",
        "mean_test_accuracy",
        "std_test_accuracy",
        "mean_fit_time",
        "params",
    ]
    return results[columns].sort_values(f"rank_test_{refit_metric}").reset_index(drop=True)


def grouped_grid_search(
    estimator: Any,
    parameter_grid: Mapping[str, Sequence[Any]],
    split: TrainValidationSplit,
    *,
    model_name: str,
    n_splits: int = 3,
    refit_metric: str = "f1_macro",
    n_jobs: int = -1,
    verbose: int = 1,
    mlflow_config: MlflowConfig | None = None,
) -> GroupedGridSearchResult:
    """Optimiza solo en training mediante GroupKFold y evalúa una vez en validación."""

    groups = split.metadata_train["subject_id"].to_numpy()
    n_subjects = len(set(groups))
    if not 2 <= n_splits <= n_subjects:
        raise ValueError(
            f"n_splits debe estar entre 2 y {n_subjects}, sujetos disponibles en training"
        )

    search = _build_search(
        estimator,
        parameter_grid,
        n_splits=n_splits,
        refit_metric=refit_metric,
        n_jobs=n_jobs,
        verbose=verbose,
    )
    search.fit(split.X_train, split.y_train, groups=groups)
    evaluation = evaluate_classifier(
        search.best_estimator_,
        split.X_validation,
        split.y_validation,
        model_name=model_name,
    )

    tracking = mlflow_config or MlflowConfig()
    if tracking.enabled:
        try:
            import mlflow
            import mlflow.sklearn

            mlflow.set_tracking_uri(tracking.tracking_uri)
            experiment = mlflow.set_experiment(tracking.experiment_name)
            with mlflow.start_run(
                experiment_id=experiment.experiment_id,
                run_name=f"grid_search_{model_name}",
            ):
                try:
                    mlflow.log_params(
                        {
                            "model_name": model_name,
                            "cv_splits": n_splits,
                            "refit_metric": refit_metric,
                            "parameter_grid": json.dumps(parameter_grid, default=str),
                            "train_epochs": len(split.X_train),
                            "validation_epochs": len(split.X_validation),
                            "train_subjects": len(split.train_subjects),
                            "validation_subjects": len(split.validation_subjects),
                        }
                    )
                    mlflow.log_params(
                        {
                            f"best_{key}": value
                            for key, value in search.best_params_.items()
                        }
                    )
                    mlflow.log_metric(
                        f"best_cv_{refit_metric}", float(search.best_score_)
                    )
                    mlflow.log_metrics(
                        {
                            f"validation_{key}": value
                            for key, value in evaluation.metrics.items()
                        }
                    )
                    if tracking.log_model:
                        mlflow.sklearn.log_model(
                            sk_model=search.best_estimator_,
                            name="model",
                            skops_trusted_types=_skops_trusted_types_for(
                                search.best_estimator_
                            ),
                        )
                except Exception as error:
                    _warn_mlflow_failure(error)
        except Exception as error:
            _warn_mlflow_failure(error)

    return GroupedGridSearchResult(
        model_name=model_name,
        best_estimator=search.best_estimator_,
        best_parameters=dict(search.best_params_),
        best_cv_score=float(search.best_score_),
        refit_metric=refit_metric,
        cv_results=_summarize_results(search, refit_metric),
        validation_evaluation=evaluation,
    )
