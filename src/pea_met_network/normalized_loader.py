from __future__ import annotations

from pathlib import Path

import pandas as pd

from pea_met_network.manifest import recognize_schema

COLUMN_RENAMES = {
    "Temperature": "air_temperature_c",
    "RH": "relative_humidity_pct",
    "Dew Point": "dew_point_c",
    "Rain": "rain_mm",
    "Wind Direction": "wind_direction_deg",
    "Solar Radiation": "solar_radiation_w_m2",
    "Battery": "battery_v",
    "Average wind speed": "wind_speed_kmh",
    "Wind gust speed": "wind_gust_speed_kmh",
    "Wind Speed": "wind_speed_ms",
    "Gust Speed": "wind_gust_speed_max_kmh",
}


def _normalized_name(column: str) -> str:
    if column in {"Date", "Time"}:
        return column
    prefix = column.split("(", 1)[0].strip()
    if prefix in COLUMN_RENAMES:
        return COLUMN_RENAMES[prefix]
    raise KeyError(f"No normalized column mapping for: {column}")


def load_normalized_station_csv(path: Path, station: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    schema = recognize_schema(frame.columns)
    rename_map = {
        col: _normalized_name(col) for col in frame.columns
    }
    renamed = frame.rename(columns=rename_map)

    timestamp_text = (
        renamed["Date"].astype(str).str.strip()
        + " "
        + renamed["Time"].astype(str).str.strip()
    )
    timestamp_utc = pd.to_datetime(
        timestamp_text,
        format="%m/%d/%Y %H:%M:%S %z",
        utc=True,
    )

    normalized = pd.DataFrame(
        {
            "station": station,
            "timestamp_utc": timestamp_utc,
        }
    )

    for column in renamed.columns:
        if column in {"Date", "Time"}:
            continue
        normalized[column] = pd.to_numeric(renamed[column], errors="coerce")

    normalized["source_file"] = str(path)
    normalized["schema_family"] = schema.family
    return normalized
