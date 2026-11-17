from pathlib import Path

import pytest

from sleep_staging.datasets import discover_sleep_cassette_records


def test_cassette_pairs_nights_without_mixing_subjects_or_orphan_files(tmp_path: Path):
    for filename in (
        "SC4061E0-PSG.edf", "SC4061EC-Hypnogram.edf",
        "SC4062E0-PSG.edf", "SC4062EH-Hypnogram.edf",
        "SC4071E0-PSG.edf", "SC4072EC-Hypnogram.edf",
    ):
        (tmp_path / filename).touch()
    records = discover_sleep_cassette_records(tmp_path)
    assert [(r.record_id, r.subject_id, r.night) for r in records] == [
        ("SC4061", "SC406", 1), ("SC4062", "SC406", 2),
    ]
    assert records[1].hypnogram_path.name == "SC4062EH-Hypnogram.edf"


def test_cassette_rejects_ambiguous_labels(tmp_path: Path):
    for name in ["SC4062E0-PSG.edf", "SC4062EC-Hypnogram.edf", "SC4062EH-Hypnogram.edf"]:
        (tmp_path / name).touch()
    with pytest.raises(ValueError, match="varios hipnogramas"):
        discover_sleep_cassette_records(tmp_path)
