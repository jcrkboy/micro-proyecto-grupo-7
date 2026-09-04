"""Construcción y división segura del dataset supervisado."""

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from sleep_staging.datasets import VALID_STAGES, SleepEdfRecord, read_epoch_labels
from sleep_staging.preprocessing import PreprocessingPipeline


@dataclass(frozen=True)
class SupervisedDataset:
    """Features, etiquetas y trazabilidad de cada época."""

    features: pd.DataFrame
    labels: pd.Series
    metadata: pd.DataFrame


@dataclass(frozen=True)
class TrainValidationSplit:
    """Partición completa con separación por sujeto."""

    X_train: pd.DataFrame
    X_validation: pd.DataFrame
    y_train: pd.Series
    y_validation: pd.Series
    metadata_train: pd.DataFrame
    metadata_validation: pd.DataFrame

    @property
    def train_subjects(self) -> tuple[str, ...]:
        return tuple(sorted(self.metadata_train["subject_id"].unique()))

    @property
    def validation_subjects(self) -> tuple[str, ...]:
        return tuple(sorted(self.metadata_validation["subject_id"].unique()))


def build_supervised_dataset(
    records: Iterable[SleepEdfRecord],
    pipeline: PreprocessingPipeline | None = None,
    *,
    verbose: bool = True,
) -> SupervisedDataset:
    """Preprocesa cada PSG y alinea después las etiquetas del hipnograma."""

    active_pipeline = pipeline or PreprocessingPipeline()
    feature_frames: list[pd.DataFrame] = []
    label_series: list[pd.Series] = []
    metadata_frames: list[pd.DataFrame] = []

    for record in records:
        result = active_pipeline.transform_edf(record.psg_path)
        labels = read_epoch_labels(
            record.hypnogram_path,
            n_epochs=len(result.features),
            epoch_seconds=active_pipeline.config.epoch_seconds,
        )
        valid = np.isin(labels, VALID_STAGES)
        features = result.features.loc[valid].reset_index(drop=True)
        metadata = result.metadata.loc[valid].reset_index(drop=True).assign(
            subject_id=record.subject_id,
            record_id=record.record_id,
            night=record.night,
        )

        feature_frames.append(features)
        label_series.append(pd.Series(labels[valid], name="stage"))
        metadata_frames.append(metadata)
        if verbose:
            print(
                f"{record.record_id}: {len(features)} épocas válidas "
                f"de {len(labels)}"
            )

    if not feature_frames:
        raise RuntimeError("No se recibió ningún registro para construir el dataset")

    features = pd.concat(feature_frames, ignore_index=True)
    labels = pd.concat(label_series, ignore_index=True)
    metadata = pd.concat(metadata_frames, ignore_index=True)
    if not (len(features) == len(labels) == len(metadata)):
        raise RuntimeError("Features, etiquetas y metadata quedaron desalineadas")
    if not np.isfinite(features.to_numpy()).all():
        raise ValueError("El dataset supervisado contiene NaN o infinitos")
    return SupervisedDataset(features, labels, metadata)


def split_by_subject(
    dataset: SupervisedDataset,
    *,
    validation_size: float = 0.2,
    random_state: int = 42,
) -> TrainValidationSplit:
    """Divide train/validación manteniendo todas las noches de un sujeto juntas."""

    if not 0 < validation_size < 1:
        raise ValueError("validation_size debe estar entre 0 y 1")
    groups = dataset.metadata["subject_id"].to_numpy()
    if len(np.unique(groups)) < 2:
        raise ValueError("Se requieren al menos dos sujetos para dividir el dataset")

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=validation_size,
        random_state=random_state,
    )
    train_indices, validation_indices = next(
        splitter.split(dataset.features, dataset.labels, groups=groups)
    )
    result = TrainValidationSplit(
        X_train=dataset.features.iloc[train_indices].reset_index(drop=True),
        X_validation=dataset.features.iloc[validation_indices].reset_index(drop=True),
        y_train=dataset.labels.iloc[train_indices].reset_index(drop=True),
        y_validation=dataset.labels.iloc[validation_indices].reset_index(drop=True),
        metadata_train=dataset.metadata.iloc[train_indices].reset_index(drop=True),
        metadata_validation=dataset.metadata.iloc[validation_indices].reset_index(drop=True),
    )
    if set(result.train_subjects) & set(result.validation_subjects):
        raise RuntimeError("Se detectó fuga de sujetos entre entrenamiento y validación")
    return result

