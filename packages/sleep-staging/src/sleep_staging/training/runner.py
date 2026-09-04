"""Entrenamiento sencillo con registro opcional en MLflow."""

import warnings
from dataclasses import dataclass
from typing import Any, Mapping

from sleep_staging.training.dataset import TrainValidationSplit
from sleep_staging.training.evaluation import ModelEvaluation, evaluate_classifier


_LIGHTGBM_SKOPS_TRUSTED_TYPES = [
    "collections.OrderedDict",
    "lightgbm.basic.Booster",
    "lightgbm.sklearn.LGBMClassifier",
]


def _skops_trusted_types_for(model: Any) -> list[str] | None:
    """Autoriza los tipos internos esperados al serializar un modelo LightGBM."""

    if model.__class__.__module__.startswith("lightgbm."):
        return _LIGHTGBM_SKOPS_TRUSTED_TYPES.copy()
    return None


def _warn_mlflow_failure(error: Exception) -> None:
    warnings.warn(
        "MLflow no pudo completar el registro; el entrenamiento y sus resultados "
        f"se conservan. Detalle: {error}",
        RuntimeWarning,
        stacklevel=2,
    )


@dataclass(frozen=True)
class MlflowConfig:
    """MLflow queda apagado por defecto para ejecuciones locales sencillas."""

    enabled: bool = False
    experiment_name: str = "sleep_staging_models"
    tracking_uri: str = "sqlite:///mlflow.db"
    log_model: bool = True


def train_and_evaluate(
    model: Any,
    split: TrainValidationSplit,
    *,
    model_name: str,
    parameters: Mapping[str, Any] | None = None,
    mlflow_config: MlflowConfig | None = None,
) -> ModelEvaluation:
    """Ajusta y evalúa un modelo; registra la corrida solo cuando se solicita."""

    model.fit(split.X_train, split.y_train)
    evaluation = evaluate_classifier(
        model,
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
                run_name=model_name,
            ):
                try:
                    logged_parameters = dict(parameters or {})
                    logged_parameters.update(
                        {
                            "train_epochs": len(split.X_train),
                            "validation_epochs": len(split.X_validation),
                            "train_subjects": len(split.train_subjects),
                            "validation_subjects": len(split.validation_subjects),
                        }
                    )
                    mlflow.log_params(logged_parameters)
                    mlflow.log_metrics(evaluation.metrics)
                    for stage, row in evaluation.per_class.iterrows():
                        mlflow.log_metric(f"f1_{stage}", float(row["f1-score"]))
                        mlflow.log_metric(f"recall_{stage}", float(row["recall"]))
                    if tracking.log_model:
                        mlflow.sklearn.log_model(
                            sk_model=model,
                            name="model",
                            skops_trusted_types=_skops_trusted_types_for(model),
                        )
                except Exception as error:
                    _warn_mlflow_failure(error)
        except Exception as error:
            _warn_mlflow_failure(error)

    return evaluation
