"""Tipos compartidos por las distintas capas del paquete."""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FilteredSignals:
    """Señal continua general y copias filtradas, expresadas en microvoltios."""

    data: np.ndarray
    slow_wave: np.ndarray
    spindle: np.ndarray
    sfreq: float
    channels: tuple[str, ...]


@dataclass(frozen=True)
class PreprocessingResult:
    """Features y trazabilidad de las épocas que las originaron."""

    features: pd.DataFrame
    metadata: pd.DataFrame
    sfreq: float
    channels: tuple[str, ...]

