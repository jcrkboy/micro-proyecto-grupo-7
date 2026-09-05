"""Genera un EDF sintético pequeño para probar el flujo de inferencia."""

from pathlib import Path

import mne
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "apps" / "api" / "tests" / "fixtures" / "sample_eeg_60s.edf"


def main() -> None:
    sfreq = 100.0
    duration_seconds = 60
    samples = int(sfreq * duration_seconds)
    time = np.arange(samples) / sfreq
    rng = np.random.default_rng(42)

    # Señales artificiales en voltios: no contienen información de ningún sujeto.
    fpz_cz = (
        35e-6 * np.sin(2 * np.pi * 2.0 * time)
        + 12e-6 * np.sin(2 * np.pi * 10.0 * time)
        + rng.normal(0.0, 4e-6, samples)
    )
    pz_oz = (
        28e-6 * np.sin(2 * np.pi * 3.0 * time + 0.4)
        + 10e-6 * np.sin(2 * np.pi * 13.0 * time)
        + rng.normal(0.0, 4e-6, samples)
    )
    info = mne.create_info(
        ch_names=["EEG Fpz-Cz", "EEG Pz-Oz"],
        sfreq=sfreq,
        ch_types=["eeg", "eeg"],
    )
    raw = mne.io.RawArray(np.vstack([fpz_cz, pz_oz]), info, verbose="ERROR")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    raw.export(OUTPUT_PATH, fmt="edf", overwrite=True, verbose="ERROR")
    print(f"EDF sintético creado: {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
