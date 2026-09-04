"""Métricas y visualización común para clasificadores de sueño."""

from dataclasses import dataclass
from typing import Any, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
)

from sleep_staging.datasets import VALID_STAGES


@dataclass(frozen=True)
class ModelEvaluation:
    """Resultado comparable de un modelo sobre validación."""

    model_name: str
    metrics: dict[str, float]
    per_class: pd.DataFrame
    confusion: pd.DataFrame
    predictions: np.ndarray


def evaluate_classifier(
    model: Any,
    X_validation: pd.DataFrame,
    y_validation: pd.Series,
    *,
    model_name: str,
    labels: Sequence[str] = VALID_STAGES,
) -> ModelEvaluation:
    """Calcula accuracy, kappa, F1 macro, reporte y matriz de confusión."""

    predictions = np.asarray(model.predict(X_validation))
    label_order = list(labels)
    report = classification_report(
        y_validation,
        predictions,
        labels=label_order,
        output_dict=True,
        zero_division=0,
    )
    per_class = pd.DataFrame(report).T.loc[label_order, ["precision", "recall", "f1-score", "support"]]
    confusion = pd.DataFrame(
        confusion_matrix(y_validation, predictions, labels=label_order),
        index=[f"real_{stage}" for stage in label_order],
        columns=[f"pred_{stage}" for stage in label_order],
    )
    metrics = {
        "accuracy": float(accuracy_score(y_validation, predictions)),
        "kappa": float(cohen_kappa_score(y_validation, predictions)),
        "f1_macro": float(
            f1_score(
                y_validation,
                predictions,
                labels=label_order,
                average="macro",
                zero_division=0,
            )
        ),
    }
    return ModelEvaluation(model_name, metrics, per_class, confusion, predictions)


def compare_evaluations(*evaluations: ModelEvaluation) -> pd.DataFrame:
    """Devuelve una tabla compacta para comparar varios modelos."""

    return pd.DataFrame(
        [evaluation.metrics for evaluation in evaluations],
        index=[evaluation.model_name for evaluation in evaluations],
    ).sort_values("f1_macro", ascending=False)


def display_evaluation(
    evaluation: ModelEvaluation,
    *,
    normalize_confusion: bool = True,
) -> None:
    """Muestra métricas, resultados por clase y matriz de confusión."""

    print(f"\n{evaluation.model_name}")
    print(pd.Series(evaluation.metrics).round(4).to_string())
    print("\nMétricas por estadio:")
    print(evaluation.per_class.round(4).to_string())

    values = evaluation.confusion.copy()
    display_format = "d"
    if normalize_confusion:
        values = values.astype(float)
        row_totals = values.sum(axis=1).replace(0, np.nan)
        values = values.div(row_totals, axis=0).fillna(0.0)
        display_format = ".2f"

    plt.figure(figsize=(7, 5))
    sns.heatmap(
        values,
        annot=True,
        fmt=display_format,
        cmap="Blues",
        vmin=0,
        vmax=1 if normalize_confusion else None,
    )
    suffix = "normalizada" if normalize_confusion else "conteos"
    plt.title(f"{evaluation.model_name} — matriz de confusión {suffix}")
    plt.ylabel("Etapa real")
    plt.xlabel("Etapa predicha")
    plt.tight_layout()
    plt.show()
