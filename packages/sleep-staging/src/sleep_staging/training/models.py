"""Factorías explícitas para los modelos comparados en notebooks."""

from typing import Any

from sklearn.ensemble import RandomForestClassifier


def create_random_forest_classifier(
    *,
    random_state: int = 42,
    **overrides: Any,
) -> RandomForestClassifier:
    """Crea el baseline Random Forest con parámetros reproducibles."""

    parameters: dict[str, Any] = {
        "n_estimators": 500,
        "min_samples_leaf": 2,
        "max_features": "sqrt",
        "class_weight": "balanced_subsample",
        "n_jobs": -1,
        "random_state": random_state,
    }
    parameters.update(overrides)
    return RandomForestClassifier(**parameters)


def create_lightgbm_classifier(
    *,
    random_state: int = 42,
    **overrides: Any,
):
    """Crea LightGBM o falla claramente si no está instalada la dependencia."""

    try:
        from lightgbm import LGBMClassifier
    except ImportError as error:
        raise ImportError(
            "LightGBM fue seleccionado pero no está instalado. "
            "Instala el extra del paquete con: pip install -e "
            "'./packages/sleep-staging[training]'"
        ) from error

    parameters: dict[str, Any] = {
        "objective": "multiclass",
        "n_estimators": 700,
        "learning_rate": 0.05,
        "num_leaves": 63,
        "min_child_samples": 40,
        "subsample": 0.8,
        "subsample_freq": 1,
        "colsample_bytree": 0.6,
        "reg_lambda": 1.0,
        "class_weight": "balanced",
        "n_jobs": -1,
        "random_state": random_state,
        "verbose": -1,
    }
    parameters.update(overrides)
    return LGBMClassifier(**parameters)

