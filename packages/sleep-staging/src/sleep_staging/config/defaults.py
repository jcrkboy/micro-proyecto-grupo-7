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
    include_subepoch_features: bool = False
    subepoch_seconds: float = 5.0
    include_signal_quality_features: bool = False
    artifact_amplitude_threshold_uv: float = 300.0
    artifact_gradient_threshold_uv: float = 100.0
    flatline_gradient_threshold_uv: float = 0.1
    temporal_difference_offsets: tuple[int, ...] = ()
    temporal_difference_tokens: tuple[str, ...] = (
        "rel_theta",
        "rel_alpha",
        "rel_beta",
        "ratio_theta_alpha",
        "huso_n_rafagas",
        "hjorth_actividad",
    )

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
        if not 0 < self.subepoch_seconds <= self.epoch_seconds:
            raise ValueError("subepoch_seconds debe estar entre cero y epoch_seconds")
        if self.artifact_amplitude_threshold_uv <= 0:
            raise ValueError("artifact_amplitude_threshold_uv debe ser positivo")
        if self.artifact_gradient_threshold_uv <= 0:
            raise ValueError("artifact_gradient_threshold_uv debe ser positivo")
        if self.flatline_gradient_threshold_uv < 0:
            raise ValueError("flatline_gradient_threshold_uv no puede ser negativo")
        if any(offset <= 0 for offset in self.temporal_difference_offsets):
            raise ValueError("Los offsets temporales deben ser enteros positivos")
