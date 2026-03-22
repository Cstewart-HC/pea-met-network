from __future__ import annotations

from pathlib import Path

import pandas as pd

from pea_met_network.materialize_resampled import materialize_resampled_outputs


def test_materialize_resampled_outputs_writes_expected_files(
    tmp_path: Path,
) -> None:
    source_path = Path(
        'data/raw/peinp/PEINP Weather Station Data 2022-2025/'
        'Cavendish/2022/PEINP_Cav_WeatherStn_Dec2022.csv'
    )

    hourly_path, daily_path = materialize_resampled_outputs(
        source_path=source_path,
        station='cavendish',
        output_dir=tmp_path,
    )

    assert hourly_path.exists()
    assert daily_path.exists()

    hourly = pd.read_csv(hourly_path)
    daily = pd.read_csv(daily_path)

    assert list(hourly.columns[:2]) == ['station', 'timestamp_utc']
    assert list(daily.columns[:2]) == ['station', 'timestamp_utc']
    assert set(hourly['station']) == {'cavendish'}
    assert set(daily['station']) == {'cavendish'}
