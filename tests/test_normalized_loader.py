from __future__ import annotations

from pathlib import Path

from pea_met_network.normalized_loader import load_normalized_station_csv


def test_load_normalized_station_csv_maps_canonical_columns() -> None:
    path = Path(
        'data/raw/peinp/PEINP Weather Station Data 2022-2025/'
        'Cavendish/2022/PEINP_Cav_WeatherStn_Dec2022.csv'
    )

    frame = load_normalized_station_csv(path, station='cavendish')

    expected = {
        'station',
        'timestamp_utc',
        'air_temperature_c',
        'relative_humidity_pct',
        'dew_point_c',
        'rain_mm',
        'wind_direction_deg',
        'solar_radiation_w_m2',
        'battery_v',
        'wind_speed_kmh',
        'wind_gust_speed_kmh',
        'wind_speed_ms',
        'wind_gust_speed_max_kmh',
        'source_file',
        'schema_family',
    }

    assert expected.issubset(frame.columns)
    assert frame.iloc[0]['station'] == 'cavendish'
    assert str(frame.iloc[0]['timestamp_utc']) == '2022-11-01 03:00:00+00:00'
    assert frame.iloc[0]['schema_family'] == 'minimal_date_time_family'
