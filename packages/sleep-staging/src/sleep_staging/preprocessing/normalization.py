"""Normalización independiente de etiquetas por registro."""

import numpy as np
import pandas as pd


def robust_normalize_record(features: pd.DataFrame) -> pd.DataFrame:
    """Aplica z-score robusto mediante mediana e IQR dentro de un registro."""

    quality_columns = [column for column in features if "_quality_" in column]
    scalable_columns = features.columns.difference(quality_columns, sort=False)
    scalable = features[scalable_columns]
    median = scalable.median()
    iqr = (
        scalable.quantile(0.75) - scalable.quantile(0.25)
    ).replace(0, np.nan).fillna(1.0)
    normalized = (scalable - median) / iqr
    result = features.copy()
    result.loc[:, scalable_columns] = normalized
    return result.replace([np.inf, -np.inf], 0.0).fillna(0.0)
