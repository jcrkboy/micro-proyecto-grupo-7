"""Carga segura de PSG EDF con el mismo filtrado usado durante entrenamiento."""

from pathlib import Path

import mne
import numpy as np

from sleep_staging.config import PreprocessingConfig
from sleep_staging.types import FilteredSignals


def load_filtered_edf(
    path: str | Path,
    config: PreprocessingConfig,
) -> FilteredSignals:
    """Lee, valida y filtra un PSG; devuelve siempre los canales en orden estable."""

    edf_path = Path(path)
    if not edf_path.is_file():
        raise FileNotFoundError(f"No existe el archivo EDF: {edf_path}")

    raw = mne.io.read_raw_edf(edf_path, preload=True, verbose="ERROR")
    missing = [channel for channel in config.channels if channel not in raw.ch_names]
    if missing:
        raise ValueError(
            f"Faltan canales requeridos {missing} en {edf_path.name}. "
            f"Disponibles: {raw.ch_names}"
        )

    sfreq = float(raw.info["sfreq"])
    if not np.isclose(sfreq, config.expected_sfreq, rtol=0.0, atol=1e-6):
        raise ValueError(
            f"Frecuencia no soportada en {edf_path.name}: {sfreq:g} Hz; "
            f"se esperaban {config.expected_sfreq:g} Hz"
        )

    raw.pick(list(config.channels))
    raw.reorder_channels(list(config.channels))
    raw.filter(
        l_freq=config.low_frequency,
        h_freq=config.high_frequency,
        verbose=False,
    )
    raw_slow_wave = raw.copy().filter(*config.slow_wave_band, verbose=False)
    raw_spindle = raw.copy().filter(*config.spindle_band, verbose=False)

    microvolts = 1e6
    return FilteredSignals(
        data=raw.get_data() * microvolts,
        slow_wave=raw_slow_wave.get_data() * microvolts,
        spindle=raw_spindle.get_data() * microvolts,
        sfreq=sfreq,
        channels=tuple(config.channels),
    )
