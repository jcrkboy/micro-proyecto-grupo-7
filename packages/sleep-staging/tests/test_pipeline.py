import numpy as np
import pytest

from sleep_staging import PreprocessingConfig, PreprocessingPipeline
from sleep_staging.types import FilteredSignals


def test_pipeline_matches_advanced_notebook_feature_shape() -> None:
    config = PreprocessingConfig()
    rng = np.random.default_rng(42)
    samples = int(config.expected_sfreq * config.epoch_seconds * 3)
    data = rng.normal(0, 20, size=(2, samples))
    signals = FilteredSignals(
        data=data,
        slow_wave=data * 0.5,
        spindle=data * 0.2,
        sfreq=config.expected_sfreq,
        channels=config.channels,
    )

    result = PreprocessingPipeline(config).transform_filtered_signals(signals)

    assert result.features.shape == (3, 486)
    assert result.metadata["epoch_index"].tolist() == [0, 1, 2]
    assert np.isfinite(result.features.to_numpy()).all()
    assert "FpzCz_rel_delta_t0" in result.features.columns
    assert "PzOz_huso_n_rafagas_t+2" in result.features.columns
    assert "inter_ratio_alpha_movil11" in result.features.columns


def test_enhanced_eeg_profile_adds_subepoch_quality_and_transition_features() -> None:
    config = PreprocessingConfig(
        rolling_windows=(3, 5, 11),
        include_subepoch_features=True,
        include_signal_quality_features=True,
        temporal_difference_offsets=(1, 2),
    )
    rng = np.random.default_rng(7)
    samples = int(config.expected_sfreq * config.epoch_seconds * 4)
    data = rng.normal(0, 20, size=(2, samples))
    signals = FilteredSignals(
        data=data,
        slow_wave=data * 0.5,
        spindle=data * 0.2,
        sfreq=config.expected_sfreq,
        channels=config.channels,
    )

    result = PreprocessingPipeline(config).transform_filtered_signals(signals)

    assert result.channels == ("EEG Fpz-Cz", "EEG Pz-Oz")
    assert result.features.shape[0] == 4
    assert result.features.shape[1] > 486
    assert np.isfinite(result.features.to_numpy()).all()
    assert "FpzCz_sub_rel_theta_std_t0" in result.features.columns
    assert "PzOz_quality_flatline_fraction_movil3" in result.features.columns
    assert "FpzCz_rel_alpha_delta_t-1" in result.features.columns
    assert "FpzCz_rel_alpha_delta_t+2" in result.features.columns
    assert result.features.loc[0, "FpzCz_rel_alpha_delta_t-1"] == 0.0
    assert result.features.loc[3, "FpzCz_rel_alpha_delta_t+1"] == 0.0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("subepoch_seconds", 0.0),
        ("artifact_amplitude_threshold_uv", 0.0),
        ("artifact_gradient_threshold_uv", -1.0),
        ("flatline_gradient_threshold_uv", -0.1),
        ("temporal_difference_offsets", (0,)),
    ],
)
def test_enhanced_preprocessing_parameters_are_validated(field: str, value: object) -> None:
    with pytest.raises(ValueError):
        PreprocessingConfig(**{field: value})
