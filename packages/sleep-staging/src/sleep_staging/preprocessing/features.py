"""Features espectrales y temporales extraídas del baseline avanzado."""

import numpy as np
import pandas as pd
from scipy import signal, stats
from scipy.integrate import trapezoid

from sleep_staging.config import PreprocessingConfig


def _channel_prefix(channel: str) -> str:
    return channel.replace("EEG ", "").replace("-", "")


def hjorth_parameters(values: np.ndarray) -> tuple[float, float, float]:
    """Calcula actividad, movilidad y complejidad de Hjorth."""

    first = np.diff(values)
    second = np.diff(first)
    var_values = float(np.var(values))
    var_first = float(np.var(first))
    var_second = float(np.var(second))
    mobility = np.sqrt(var_first / var_values) if var_values > 0 else 0.0
    first_mobility = np.sqrt(var_second / var_first) if var_first > 0 else 0.0
    complexity = first_mobility / mobility if mobility > 0 else 0.0
    return var_values, float(mobility), float(complexity)


def _spectral_band_powers(
    values: np.ndarray,
    sfreq: float,
    config: PreprocessingConfig,
) -> dict[str, float]:
    """Calcula potencias por banda con el estimador robusto común."""

    nperseg = min(len(values), int(4 * sfreq))
    frequencies, psd = signal.welch(
        values,
        fs=sfreq,
        nperseg=nperseg,
        average="median",
    )
    powers: dict[str, float] = {}
    for name, (low, high) in config.bands.items():
        mask = (frequencies >= low) & (frequencies < high)
        powers[name] = (
            float(trapezoid(psd[mask], frequencies[mask])) if mask.any() else 0.0
        )
    return powers


def _linear_slope(values: np.ndarray) -> float:
    """Pendiente sobre posiciones normalizadas; estable para cualquier longitud."""

    if len(values) < 2:
        return 0.0
    positions = np.linspace(0.0, 1.0, len(values))
    return float(np.polyfit(positions, values, deg=1)[0])


def _subepoch_features(
    values: np.ndarray,
    sfreq: float,
    prefix: str,
    config: PreprocessingConfig,
) -> dict[str, float]:
    """Describe cambios espectrales dentro de una época EEG de 30 segundos."""

    samples_per_chunk = int(round(config.subepoch_seconds * sfreq))
    chunk_count = len(values) // samples_per_chunk
    if chunk_count < 2:
        return {}

    epsilon = 1e-12
    chunks = values[: chunk_count * samples_per_chunk].reshape(
        chunk_count, samples_per_chunk
    )
    relative: dict[str, list[float]] = {
        band: [] for band in ("theta", "alpha", "sigma", "beta")
    }
    rms_values: list[float] = []
    for chunk in chunks:
        powers = _spectral_band_powers(chunk, sfreq, config)
        total = sum(power for name, power in powers.items() if name != "sw")
        for band in relative:
            relative[band].append(powers[band] / total if total > 0 else 0.0)
        rms_values.append(float(np.sqrt(np.mean(chunk**2))))

    result: dict[str, float] = {}
    arrays = {band: np.asarray(values_) for band, values_ in relative.items()}
    for band, band_values in arrays.items():
        result[f"{prefix}_sub_rel_{band}_mean"] = float(np.mean(band_values))
        result[f"{prefix}_sub_rel_{band}_std"] = float(np.std(band_values))
        result[f"{prefix}_sub_rel_{band}_range"] = float(np.ptp(band_values))

    theta_alpha = arrays["theta"] / (arrays["alpha"] + epsilon)
    result[f"{prefix}_sub_theta_alpha_ratio_mean"] = float(np.mean(theta_alpha))
    result[f"{prefix}_sub_theta_alpha_ratio_std"] = float(np.std(theta_alpha))
    result[f"{prefix}_sub_theta_alpha_ratio_max"] = float(np.max(theta_alpha))
    result[f"{prefix}_sub_theta_dominant_fraction"] = float(
        np.mean(arrays["theta"] > arrays["alpha"])
    )
    result[f"{prefix}_sub_alpha_slope"] = _linear_slope(arrays["alpha"])
    result[f"{prefix}_sub_theta_slope"] = _linear_slope(arrays["theta"])
    result[f"{prefix}_sub_rms_mean"] = float(np.mean(rms_values))
    result[f"{prefix}_sub_rms_std"] = float(np.std(rms_values))
    return result


def _signal_quality_features(
    values: np.ndarray,
    prefix: str,
    config: PreprocessingConfig,
) -> dict[str, float]:
    """Cuantifica artefactos sin descartar épocas ni desalinear etiquetas."""

    gradients = np.abs(np.diff(values))
    return {
        f"{prefix}_quality_extreme_amplitude_fraction": float(
            np.mean(np.abs(values) > config.artifact_amplitude_threshold_uv)
        ),
        f"{prefix}_quality_extreme_gradient_fraction": float(
            np.mean(gradients > config.artifact_gradient_threshold_uv)
        ),
        f"{prefix}_quality_flatline_fraction": float(
            np.mean(gradients <= config.flatline_gradient_threshold_uv)
        ),
        f"{prefix}_quality_max_abs": float(np.max(np.abs(values))),
        f"{prefix}_quality_max_gradient": float(np.max(gradients)),
    }


def extract_channel_features(
    values: np.ndarray,
    slow_wave: np.ndarray,
    spindle: np.ndarray,
    sfreq: float,
    prefix: str,
    config: PreprocessingConfig,
) -> dict[str, float]:
    """Extrae las 37 features de un canal para una época."""

    result: dict[str, float] = {}
    epsilon = 1e-12
    nperseg = min(len(values), int(4 * sfreq))
    frequencies, psd = signal.welch(
        values,
        fs=sfreq,
        nperseg=nperseg,
        average="median",
    )

    powers: dict[str, float] = {}
    for name, (low, high) in config.bands.items():
        mask = (frequencies >= low) & (frequencies < high)
        powers[name] = (
            float(trapezoid(psd[mask], frequencies[mask])) if mask.any() else 0.0
        )

    total = sum(power for name, power in powers.items() if name != "sw")
    for name, power in powers.items():
        result[f"{prefix}_rel_{name}"] = power / total if total > 0 else 0.0
        result[f"{prefix}_log_{name}"] = float(np.log10(power + epsilon))

    result[f"{prefix}_ratio_delta_beta"] = powers["delta"] / (powers["beta"] + epsilon)
    result[f"{prefix}_ratio_theta_alpha"] = powers["theta"] / (powers["alpha"] + epsilon)
    result[f"{prefix}_ratio_delta_theta"] = powers["delta"] / (powers["theta"] + epsilon)
    result[f"{prefix}_ratio_alpha_beta"] = powers["alpha"] / (powers["beta"] + epsilon)
    result[f"{prefix}_ratio_sigma_theta"] = powers["sigma"] / (powers["theta"] + epsilon)

    useful = (
        (frequencies >= config.useful_band[0])
        & (frequencies <= config.useful_band[1])
    )
    useful_frequencies = frequencies[useful]
    useful_psd = psd[useful]
    normalized_psd = useful_psd / (useful_psd.sum() + epsilon)
    result[f"{prefix}_entropia_espectral"] = float(
        -np.sum(normalized_psd * np.log2(normalized_psd + epsilon))
    )

    cumulative = np.cumsum(useful_psd)
    if len(cumulative) and cumulative[-1] > 0:
        cumulative = cumulative / cumulative[-1]
        result[f"{prefix}_freq_mediana"] = float(
            useful_frequencies[np.searchsorted(cumulative, 0.50)]
        )
        result[f"{prefix}_sef95"] = float(
            useful_frequencies[np.searchsorted(cumulative, 0.95)]
        )
    else:
        result[f"{prefix}_freq_mediana"] = 0.0
        result[f"{prefix}_sef95"] = 0.0

    result[f"{prefix}_std"] = float(np.std(values))
    result[f"{prefix}_ptp"] = float(np.ptp(values))
    result[f"{prefix}_kurtosis"] = float(stats.kurtosis(values))
    result[f"{prefix}_skew"] = float(stats.skew(values))
    result[f"{prefix}_p75_abs"] = float(np.percentile(np.abs(values), 75))
    result[f"{prefix}_zcr"] = float(np.mean(np.diff(np.signbit(values)) != 0))

    activity, mobility, complexity = hjorth_parameters(values)
    result[f"{prefix}_hjorth_actividad"] = activity
    result[f"{prefix}_hjorth_movilidad"] = mobility
    result[f"{prefix}_hjorth_complejidad"] = complexity

    slow_envelope = np.abs(signal.hilbert(slow_wave))
    result[f"{prefix}_sw_frac75"] = float(np.mean(slow_envelope > 37.5))
    result[f"{prefix}_sw_frac40"] = float(np.mean(slow_envelope > 20.0))
    result[f"{prefix}_sw_env_p90"] = float(np.percentile(slow_envelope, 90))
    result[f"{prefix}_sw_rms"] = float(np.sqrt(np.mean(slow_wave**2)))

    spindle_envelope = np.abs(signal.hilbert(spindle))
    spindle_median = float(np.median(spindle_envelope)) + epsilon
    result[f"{prefix}_huso_rms"] = float(np.sqrt(np.mean(spindle**2)))
    result[f"{prefix}_huso_env_p90"] = float(np.percentile(spindle_envelope, 90))
    result[f"{prefix}_huso_pico_med"] = float(np.max(spindle_envelope) / spindle_median)

    above = spindle_envelope > 2.0 * spindle_median
    edges = np.diff(np.concatenate(([0], above.astype(int), [0])))
    starts, ends = np.where(edges == 1)[0], np.where(edges == -1)[0]
    durations = (ends - starts) / sfreq
    result[f"{prefix}_huso_n_rafagas"] = float(
        np.sum((durations >= 0.5) & (durations <= 2.0))
    )
    if config.include_subepoch_features:
        result.update(_subepoch_features(values, sfreq, prefix, config))
    if config.include_signal_quality_features:
        result.update(_signal_quality_features(values, prefix, config))
    return result


def extract_epoch_features(
    epochs: np.ndarray,
    slow_wave_epochs: np.ndarray,
    spindle_epochs: np.ndarray,
    sfreq: float,
    channels: tuple[str, ...],
    config: PreprocessingConfig,
) -> pd.DataFrame:
    """Construye una fila de features base por época."""

    if epochs.shape != slow_wave_epochs.shape or epochs.shape != spindle_epochs.shape:
        raise ValueError("Las tres matrices de épocas deben tener la misma forma")
    if epochs.ndim != 3 or epochs.shape[1] != len(channels):
        raise ValueError("Las épocas no coinciden con la cantidad de canales")

    rows: list[dict[str, float]] = []
    n_epochs = epochs.shape[0]
    for epoch_index in range(n_epochs):
        row: dict[str, float] = {}
        for channel_index, channel in enumerate(channels):
            row.update(
                extract_channel_features(
                    epochs[epoch_index, channel_index],
                    slow_wave_epochs[epoch_index, channel_index],
                    spindle_epochs[epoch_index, channel_index],
                    sfreq,
                    _channel_prefix(channel),
                    config,
                )
            )
        row["pos_relativa"] = epoch_index / max(1, n_epochs - 1)
        rows.append(row)

    features = pd.DataFrame(rows)
    # Las dos primeras derivaciones configuradas son el par EEG actual. Mantener
    # esta lógica con >= 2 permite agregar modalidades futuras sin perder estas
    # relaciones entre derivaciones EEG.
    if len(channels) >= 2:
        first, second = map(_channel_prefix, channels)
        epsilon = 1e-12
        for band in ("delta", "theta", "alpha", "sigma", "beta"):
            features[f"inter_ratio_{band}"] = (
                features[f"{first}_rel_{band}"]
                / (features[f"{second}_rel_{band}"] + epsilon)
            )
        features["inter_ratio_std"] = (
            features[f"{first}_std"] / (features[f"{second}_std"] + epsilon)
        )
    return features
