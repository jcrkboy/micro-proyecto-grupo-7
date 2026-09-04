import numpy as np

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

