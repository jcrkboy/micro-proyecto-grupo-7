"""Contrato del bundle exportado por el notebook de entrenamiento."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from sleep_staging.config import PreprocessingConfig


_TUPLE_FIELDS = {
    "channels",
    "slow_wave_band",
    "spindle_band",
    "useful_band",
    "rolling_windows",
    "temporal_difference_offsets",
    "temporal_difference_tokens",
}


@dataclass(frozen=True)
class ModelManifest:
    """Metadatos mínimos necesarios para reproducir la inferencia."""

    artifact_version: int
    model_type: str
    model_file: str
    classes: tuple[str, ...]
    feature_columns: tuple[str, ...]
    preprocessing: PreprocessingConfig
    raw: dict[str, Any]


def load_manifest(path: str | Path) -> ModelManifest:
    """Lee y valida el manifiesto generado junto al modelo LightGBM."""

    manifest_path = Path(path)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"No existe el manifiesto: {manifest_path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"El manifiesto no contiene JSON válido: {exc}") from exc

    required = {
        "artifact_version",
        "model_type",
        "model_file",
        "classes",
        "feature_columns",
        "preprocessing",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"Faltan campos requeridos en el manifiesto: {missing}")

    classes = tuple(str(value) for value in payload["classes"])
    feature_columns = tuple(str(value) for value in payload["feature_columns"])
    if not classes or len(set(classes)) != len(classes):
        raise ValueError("Las clases del manifiesto deben ser únicas y no vacías")
    if not feature_columns or len(set(feature_columns)) != len(feature_columns):
        raise ValueError("Las features del manifiesto deben ser únicas y no vacías")

    config_payload = dict(payload["preprocessing"])
    for field in _TUPLE_FIELDS:
        if field in config_payload:
            config_payload[field] = tuple(config_payload[field])
    if "bands" in config_payload:
        config_payload["bands"] = {
            name: tuple(bounds) for name, bounds in config_payload["bands"].items()
        }

    return ModelManifest(
        artifact_version=int(payload["artifact_version"]),
        model_type=str(payload["model_type"]),
        model_file=str(payload["model_file"]),
        classes=classes,
        feature_columns=feature_columns,
        preprocessing=PreprocessingConfig(**config_payload),
        raw=payload,
    )
