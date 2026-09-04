import numpy as np
import pytest

from sleep_staging.preprocessing.epoching import segment_signal


def test_segment_signal_returns_epochs_channels_samples() -> None:
    data = np.arange(2 * 6_500, dtype=float).reshape(2, 6_500)

    epochs = segment_signal(data, sfreq=100.0, epoch_seconds=30.0)

    assert epochs.shape == (2, 2, 3_000)
    np.testing.assert_array_equal(epochs[0, 0], data[0, :3_000])
    np.testing.assert_array_equal(epochs[1, 1], data[1, 3_000:6_000])


def test_segment_signal_rejects_short_record() -> None:
    with pytest.raises(ValueError, match="época completa"):
        segment_signal(np.zeros((2, 2_999)), sfreq=100.0, epoch_seconds=30.0)

