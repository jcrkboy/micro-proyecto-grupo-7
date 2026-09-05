"""Predictor de estadios del sueño independiente de FastAPI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from sleep_staging.inference.artifacts import ModelManifest, load_manifest
from sleep_staging.preprocessing import PreprocessingPipeline


@dataclass(frozen=True)
class PredictionResult:
    """Predicción por época y metadatos necesarios para el hipnograma."""

    stages: tuple[str, ...]
    probabilities: np.ndarray
    onset_seconds: np.ndarray
    duration_seconds: np.ndarray
    sfreq: float
    channels: tuple[str, ...]


class SleepStagePredictor:
    """Carga el bundle una vez y predice PSG EDF completos."""

    def __init__(self, artifact_dir: str | Path) -> None:
        artifact_path = Path(artifact_dir).expanduser().resolve()
        self.manifest: ModelManifest = load_manifest(artifact_path / "manifest.json")
        if self.manifest.model_type != "LightGBM Booster":
            raise ValueError(
                f"Tipo de modelo no soportado: {self.manifest.model_type!r}"
            )

        model_path = (artifact_path / self.manifest.model_file).resolve()
        if not model_path.is_relative_to(artifact_path):
            raise ValueError("La ruta del modelo sale del directorio del artefacto")
        if not model_path.is_file():
            raise FileNotFoundError(f"No existe el modelo: {model_path}")

        try:
            from lightgbm import Booster
        except ImportError as exc:  # pragma: no cover - depende de la instalación
            raise RuntimeError(
                "LightGBM no está instalado; instale sleep-staging[inference]"
            ) from exc

        self.artifact_dir = artifact_path
        self.model = Booster(model_file=str(model_path))
        if self.model.num_feature() != len(self.manifest.feature_columns):
            raise ValueError(
                "El número de features del modelo no coincide con el manifiesto: "
                f"{self.model.num_feature()} != {len(self.manifest.feature_columns)}"
            )
        self.pipeline = PreprocessingPipeline(self.manifest.preprocessing)

    @property
    def model_version(self) -> str:
        return f"artifact-v{self.manifest.artifact_version}"

    def predict_edf(self, path: str | Path) -> PredictionResult:
        """Preprocesa un PSG y devuelve estadio y probabilidades por época."""

        try:
            processed = self.pipeline.transform_edf(path)
        except (OSError, RuntimeError) as exc:
            raise ValueError(f"No fue posible procesar el EDF: {exc}") from exc
        actual_columns = tuple(processed.features.columns)
        missing = sorted(set(self.manifest.feature_columns) - set(actual_columns))
        if missing:
            raise ValueError(
                f"El preprocesamiento no produjo {len(missing)} features requeridas; "
                f"primeras: {missing[:5]}"
            )

        feature_frame = processed.features.loc[:, self.manifest.feature_columns]
        probabilities = np.asarray(self.model.predict(feature_frame), dtype=float)
        expected_shape = (len(feature_frame), len(self.manifest.classes))
        if probabilities.shape != expected_shape:
            raise ValueError(
                f"El modelo devolvió forma {probabilities.shape}; se esperaba {expected_shape}"
            )
        if not np.isfinite(probabilities).all():
            raise ValueError("El modelo devolvió probabilidades no finitas")

        class_array = np.asarray(self.manifest.classes)
        stages = tuple(class_array[np.argmax(probabilities, axis=1)].tolist())
        return PredictionResult(
            stages=stages,
            probabilities=probabilities,
            onset_seconds=processed.metadata["onset_seconds"].to_numpy(dtype=float),
            duration_seconds=processed.metadata["duration_seconds"].to_numpy(dtype=float),
            sfreq=processed.sfreq,
            channels=processed.channels,
        )
