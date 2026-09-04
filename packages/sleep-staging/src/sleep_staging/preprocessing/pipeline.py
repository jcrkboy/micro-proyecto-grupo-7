"""Orquestador único de preprocesamiento para entrenamiento e inferencia."""

from pathlib import Path

import numpy as np
import pandas as pd

from sleep_staging.config import PreprocessingConfig
from sleep_staging.io import load_filtered_edf
from sleep_staging.preprocessing.context import add_temporal_context
from sleep_staging.preprocessing.epoching import segment_signal
from sleep_staging.preprocessing.features import extract_epoch_features
from sleep_staging.preprocessing.normalization import robust_normalize_record
from sleep_staging.types import FilteredSignals, PreprocessingResult


class PreprocessingPipeline:
    """Transforma un PSG completo sin depender de etiquetas o hipnogramas."""

    def __init__(self, config: PreprocessingConfig | None = None) -> None:
        self.config = config or PreprocessingConfig()

    def transform_edf(self, path: str | Path) -> PreprocessingResult:
        """Carga un EDF y produce features listas para el modelo."""

        return self.transform_filtered_signals(load_filtered_edf(path, self.config))

    def transform_filtered_signals(
        self,
        signals: FilteredSignals,
    ) -> PreprocessingResult:
        """Transforma señales ya filtradas; útil para pruebas y procesos batch."""

        if tuple(signals.channels) != tuple(self.config.channels):
            raise ValueError(
                "Los canales filtrados no coinciden, en contenido y orden, "
                "con la configuración del pipeline"
            )
        if not np.isclose(signals.sfreq, self.config.expected_sfreq, atol=1e-6):
            raise ValueError("La frecuencia de las señales no coincide con la configuración")

        epochs = segment_signal(
            signals.data,
            signals.sfreq,
            self.config.epoch_seconds,
        )
        slow_wave_epochs = segment_signal(
            signals.slow_wave,
            signals.sfreq,
            self.config.epoch_seconds,
        )
        spindle_epochs = segment_signal(
            signals.spindle,
            signals.sfreq,
            self.config.epoch_seconds,
        )

        base_features = extract_epoch_features(
            epochs,
            slow_wave_epochs,
            spindle_epochs,
            signals.sfreq,
            signals.channels,
            self.config,
        )
        if self.config.normalize_per_record:
            base_features = robust_normalize_record(base_features)
        features = add_temporal_context(
            base_features,
            neighbors=self.config.context_neighbors,
            rolling_windows=self.config.rolling_windows,
        )
        features = features.replace([np.inf, -np.inf], 0.0).fillna(0.0)
        if not np.isfinite(features.to_numpy()).all():
            raise ValueError("El preprocesamiento generó features no finitas")

        metadata = pd.DataFrame(
            {
                "epoch_index": np.arange(len(features), dtype=int),
                "onset_seconds": np.arange(len(features)) * self.config.epoch_seconds,
                "duration_seconds": self.config.epoch_seconds,
            }
        )
        return PreprocessingResult(
            features=features,
            metadata=metadata,
            sfreq=signals.sfreq,
            channels=signals.channels,
        )

