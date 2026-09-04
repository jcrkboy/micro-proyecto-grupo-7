"""Valores versionados del pipeline EEG."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PreprocessingConfig:
    """Parámetros que deben coincidir entre entrenamiento e inferencia."""

    channels: tuple[str, ...] = ("EEG Fpz-Cz", "EEG Pz-Oz")
    expected_sfreq: float = 100.0
    epoch_seconds: float = 30.0
    low_frequency: float = 0.3
    high_frequency: float = 35.0
    slow_wave_band: tuple[float, float] = (0.5, 2.0)
    spindle_band: tuple[float, float] = (11.0, 16.0)
    useful_band: tuple[float, float] = (0.5, 30.0)
    bands: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            "sw": (0.5, 2.0),
            "delta": (0.5, 4.0),
            "theta": (4.0, 8.0),
            "alpha": (8.0, 12.0),
            "sigma": (12.0, 16.0),
            "beta": (16.0, 30.0),
        }
    )
    normalize_per_record: bool = True
    context_neighbors: int = 2
    rolling_windows: tuple[int, ...] = (11,)

    def __post_init__(self) -> None:
        if not self.channels:
            raise ValueError("Se requiere al menos un canal EEG")
        if self.expected_sfreq <= 0 or self.epoch_seconds <= 0:
            raise ValueError("La frecuencia y la duración de época deben ser positivas")
        if not 0 <= self.low_frequency < self.high_frequency:
            raise ValueError("La banda de filtrado general no es válida")
        if self.high_frequency >= self.expected_sfreq / 2:
            raise ValueError("high_frequency debe ser menor que la frecuencia de Nyquist")
        if self.context_neighbors < 0:
            raise ValueError("context_neighbors no puede ser negativo")
        if any(window <= 0 or window % 2 == 0 for window in self.rolling_windows):
            raise ValueError("Las ventanas móviles deben ser enteros impares positivos")

