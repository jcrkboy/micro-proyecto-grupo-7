"""Pareo y etiquetas del subset Sleep Telemetry de Sleep-EDFx."""

from dataclasses import dataclass
from pathlib import Path
import re

import mne
import numpy as np


RECORD_PATTERN = re.compile(r"^ST7(\d{2})(\d)J0-PSG\.edf$", re.IGNORECASE)
STAGE_MAPPING = {
    "Sleep stage W": "W",
    "Sleep stage 1": "N1",
    "Sleep stage 2": "N2",
    "Sleep stage 3": "N3",
    "Sleep stage 4": "N3",
    "Sleep stage R": "REM",
}
VALID_STAGES = ("W", "N1", "N2", "N3", "REM")


@dataclass(frozen=True)
class SleepEdfRecord:
    """Par PSG/hipnograma con identificadores para agrupar por sujeto."""

    psg_path: Path
    hypnogram_path: Path
    record_id: str
    subject_id: str
    night: int


def discover_sleep_telemetry_records(base: str | Path) -> list[SleepEdfRecord]:
    """Descubre pares válidos sin asumir rutas personales o de Colab."""

    data_dir = Path(base)
    if not data_dir.is_dir():
        raise FileNotFoundError(f"No existe el directorio de datos: {data_dir}")

    records: list[SleepEdfRecord] = []
    for psg_path in sorted(data_dir.glob("*-PSG.edf")):
        match = RECORD_PATTERN.match(psg_path.name)
        if match is None:
            continue
        subject_number, night = match.groups()
        candidates = sorted(
            data_dir.glob(f"ST7{subject_number}{night}J?-Hypnogram.edf")
        )
        if candidates:
            records.append(
                SleepEdfRecord(
                    psg_path=psg_path,
                    hypnogram_path=candidates[0],
                    record_id=f"ST7{subject_number}{night}",
                    subject_id=f"S{subject_number}",
                    night=int(night),
                )
            )

    if not records:
        raise RuntimeError(f"No se encontraron pares Sleep Telemetry en {data_dir}")
    return records


def read_epoch_labels(
    hypnogram_path: str | Path,
    n_epochs: int,
    epoch_seconds: float = 30.0,
) -> np.ndarray:
    """Alinea las anotaciones clínicas a las épocas; uso exclusivo de entrenamiento."""

    labels = np.full(n_epochs, None, dtype=object)
    annotations = mne.read_annotations(hypnogram_path)
    for onset, duration, description in zip(
        annotations.onset,
        annotations.duration,
        annotations.description,
    ):
        stage = STAGE_MAPPING.get(str(description).strip())
        if stage is None:
            continue
        start = max(0, int(np.floor(onset / epoch_seconds)))
        end = min(n_epochs, int(np.ceil((onset + duration) / epoch_seconds)))
        labels[start:end] = stage
    return labels

