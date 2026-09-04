"""Normalización independiente de etiquetas por registro."""

import numpy as np
import pandas as pd


def robust_normalize_record(features: pd.DataFrame) -> pd.DataFrame:
    """Aplica z-score robusto mediante mediana e IQR dentro de un registro."""

    median = features.median()
    iqr = (
        features.quantile(0.75) - features.quantile(0.25)
    ).replace(0, np.nan).fillna(1.0)
    normalized = (features - median) / iqr
    return normalized.replace([np.inf, -np.inf], 0.0).fillna(0.0)

