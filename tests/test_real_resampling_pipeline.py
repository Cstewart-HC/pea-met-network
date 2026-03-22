from __future__ import annotations

from pathlib import Path

from pea_met_network.normalized_loader import load_normalized_station_csv
from pea_met_network.resampling import resample_daily, resample_hourly


def test_real_file_resampling_produces_hourly_and_daily_frames() -> None:
    path = Path(
        'data/raw/peinp/PEINP Weather Station Data 2022-2025/'
        'Cavendish/2022/PEINP_Cav_WeatherStn_Dec2022.csv'
    )

    normalized = load_normalized_station_csv(path, station='cavendish')
    hourly = resample_hourly(normalized)
    daily = resample_daily(normalized)

    assert not normalized.empty
    assert not hourly.empty
    assert not daily.empty
    assert list(hourly.columns[:2]) == ['station', 'timestamp_utc']
    assert list(daily.columns[:2]) == ['station', 'timestamp_utc']
    assert hourly['station'].nunique() == 1
    assert daily['station'].nunique() == 1
    assert hourly['timestamp_utc'].is_monotonic_increasing
    assert daily['timestamp_utc'].is_monotonic_increasing
    assert str(hourly.iloc[0]['timestamp_utc'].tz) == 'UTC'
    assert str(daily.iloc[0]['timestamp_utc'].tz) == 'UTC'
