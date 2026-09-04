"""Caché compartible del dataset supervisado preprocesado."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from sleep_staging.datasets import SleepEdfRecord
from sleep_staging.preprocessing import PreprocessingPipeline
from sleep_staging.training.dataset import SupervisedDataset, build_supervised_dataset


CACHE_SCHEMA_VERSION = 2


def _cache_payload(
    records: tuple[SleepEdfRecord, ...],
    pipeline: PreprocessingPipeline,
) -> dict[str, object]:
    """Describe las entradas que deben producir exactamente el mismo dataset."""

    files = []
    for record in records:
        for kind, path in (
            ("psg", record.psg_path),
            ("hypnogram", record.hypnogram_path),
        ):
            file_path = Path(path)
            files.append(
                {
                    "kind": kind,
                    "name": file_path.name,
                    "size": file_path.stat().st_size,
                }
            )

    return {
        "schema_version": CACHE_SCHEMA_VERSION,
        "record_ids": [record.record_id for record in records],
        "files": files,
        "preprocessing": asdict(pipeline.config),
    }


def _cache_key(payload: dict[str, object]) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()[:12]


def _validate_dataset(dataset: SupervisedDataset) -> None:
    if not (
        len(dataset.features) == len(dataset.labels) == len(dataset.metadata)
    ):
        raise RuntimeError("El dataset almacenado está desalineado")
    if not np.isfinite(dataset.features.to_numpy()).all():
        raise ValueError("El dataset almacenado contiene NaN o infinitos")


def _write_parquet(frame: pd.DataFrame, destination: Path) -> None:
    """Escribe primero un temporal para no dejar un archivo parcial."""

    temporary = destination.with_suffix(f"{destination.suffix}.tmp")
    frame.to_parquet(temporary, index=False)
    temporary.replace(destination)


def load_or_build_supervised_dataset(
    records: Iterable[SleepEdfRecord],
    pipeline: PreprocessingPipeline,
    cache_root: str | Path,
    *,
    verbose: bool = True,
) -> SupervisedDataset:
    """Carga un dataset compatible del caché o lo construye y persiste.

    ``cache_root`` puede vivir en ``data/processed`` y compartirse mediante DVC.
    Hay que incrementar ``CACHE_SCHEMA_VERSION`` cuando cambie la lógica de
    construcción o extracción de features de una forma no expresada en la
    configuración de preprocesamiento.
    """

    selected_records = tuple(records)
    if not selected_records:
        raise ValueError("Se requiere al menos un registro para construir el dataset")

    payload = _cache_payload(selected_records, pipeline)
    cache_directory = Path(cache_root) / _cache_key(payload)
    features_path = cache_directory / "features.parquet"
    labels_path = cache_directory / "labels.parquet"
    metadata_path = cache_directory / "metadata.parquet"
    manifest_path = cache_directory / "manifest.json"

    if all(
        path.is_file()
        for path in (features_path, labels_path, metadata_path, manifest_path)
    ):
        if verbose:
            print(f"Cargando dataset desde caché: {cache_directory}")
        dataset = SupervisedDataset(
            features=pd.read_parquet(features_path),
            labels=pd.read_parquet(labels_path)["stage"],
            metadata=pd.read_parquet(metadata_path),
        )
        _validate_dataset(dataset)
        return dataset

    if verbose:
        print(f"Construyendo dataset para {len(selected_records)} registros...")
    dataset = build_supervised_dataset(
        selected_records,
        pipeline,
        verbose=verbose,
    )
    _validate_dataset(dataset)

    cache_directory.mkdir(parents=True, exist_ok=True)
    _write_parquet(dataset.features, features_path)
    _write_parquet(dataset.labels.rename("stage").to_frame(), labels_path)
    _write_parquet(dataset.metadata, metadata_path)
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    if verbose:
        print(f"Dataset guardado en caché: {cache_directory}")
    return dataset
