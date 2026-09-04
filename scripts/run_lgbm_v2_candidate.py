"""Ejecuta un candidato LightGBM sobre el caché EEG v2 y lo registra en MLflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SRC = REPO_ROOT / "packages" / "sleep-staging" / "src"
if str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))

from sleep_staging import PreprocessingConfig, PreprocessingPipeline
from sleep_staging.datasets import discover_sleep_telemetry_records
from sleep_staging.training import (
    MlflowConfig,
    create_lightgbm_classifier,
    load_or_build_supervised_dataset,
    split_by_subject,
    train_and_evaluate,
)


DEFAULT_CLASS_WEIGHT = {
    "N1": 2.20,
    "N2": 0.41,
    "N3": 1.56,
    "REM": 1.00,
    "W": 2.01,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        metavar="KEY=JSON_VALUE",
        help="Override repetible, por ejemplo --set num_leaves=32",
    )
    parser.add_argument("--n1-weight", type=float)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    overrides: dict[str, object] = {}
    for item in args.overrides:
        key, separator, raw_value = item.partition("=")
        if not separator or not key:
            raise ValueError(f"Override inválido: {item!r}")
        overrides[key] = json.loads(raw_value)
    parameters = {
        "boosting_type": "dart",
        "learning_rate": 0.025,
        "min_child_samples": 25,
        "n_estimators": 800,
        "num_leaves": 36,
        "max_depth": 8,
        "drop_rate": 0.10,
        "skip_drop": 0.50,
        "reg_alpha": 0.10,
        "reg_lambda": 1.50,
        "class_weight": DEFAULT_CLASS_WEIGHT.copy(),
    }
    parameters.update(overrides)
    if args.n1_weight is not None:
        parameters["class_weight"] = {
            **DEFAULT_CLASS_WEIGHT,
            "N1": args.n1_weight,
        }

    preprocessing = PreprocessingConfig(
        channels=("EEG Fpz-Cz", "EEG Pz-Oz"),
        rolling_windows=(3, 5, 11),
        include_subepoch_features=True,
        subepoch_seconds=5.0,
        include_signal_quality_features=True,
        temporal_difference_offsets=(1, 2),
    )
    records = discover_sleep_telemetry_records(REPO_ROOT / "data" / "sleep-telemetry")
    dataset = load_or_build_supervised_dataset(
        records,
        PreprocessingPipeline(preprocessing),
        REPO_ROOT / "data" / "processed" / "supervised",
        verbose=False,
    )
    split = split_by_subject(dataset, validation_size=0.20, random_state=42)
    model = create_lightgbm_classifier(random_state=42, **parameters)
    evaluation = train_and_evaluate(
        model,
        split,
        model_name=args.name,
        parameters=parameters,
        mlflow_config=MlflowConfig(
            enabled=True,
            experiment_name="sleep_staging_model_comparison",
            tracking_uri="http://54.226.66.252:5000/",
            log_model=False,
        ),
    )
    result = {
        "name": args.name,
        "parameters": parameters,
        "accuracy": evaluation.metrics["accuracy"],
        "f1_macro": evaluation.metrics["f1_macro"],
        "f1_N1": float(evaluation.per_class.loc["N1", "f1-score"]),
        "precision_N1": float(evaluation.per_class.loc["N1", "precision"]),
        "recall_N1": float(evaluation.per_class.loc["N1", "recall"]),
    }
    print("RESULT_JSON=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
