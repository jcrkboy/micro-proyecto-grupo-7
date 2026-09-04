"""Segmentación de señales continuas en épocas no solapadas."""

import numpy as np


def segment_signal(data: np.ndarray, sfreq: float, epoch_seconds: float) -> np.ndarray:
    """Convierte ``(canales, muestras)`` en ``(épocas, canales, muestras)``."""

    values = np.asarray(data, dtype=float)
    if values.ndim != 2:
        raise ValueError("La señal debe tener forma (canales, muestras)")
    if not np.isfinite(values).all():
        raise ValueError("La señal contiene NaN o infinitos")

    samples_per_epoch = int(round(epoch_seconds * sfreq))
    if samples_per_epoch <= 0:
        raise ValueError("La duración de época produce cero muestras")

    n_epochs = values.shape[1] // samples_per_epoch
    if n_epochs == 0:
        raise ValueError(
            f"La señal no alcanza una época completa de {epoch_seconds:g} segundos"
        )

    trimmed = values[:, : n_epochs * samples_per_epoch]
    epochs = trimmed.reshape(values.shape[0], n_epochs, samples_per_epoch)
    return np.transpose(epochs, (1, 0, 2))

