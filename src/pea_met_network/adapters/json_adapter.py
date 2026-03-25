"""JSON adapter for Licor Cloud API responses."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pea_met_network.adapters.base import BaseAdapter

# Map Licor measurement types to canonical column names.
# Wind speed comes in m/s from the API, so we store as wind_speed_ms
# and let derive_wind_speed_kmh convert it.
LICOR_MEASUREMENT_MAP: dict[str, str] = {
    "Temperature": "air_temperature_c",
    "RH": "relative_humidity_pct",
    "Dew Point": "dew_point_c",
    "Rain": "rain_mm",
    "Accumulated Rain": "accumulated_rain_mm",  # will be dropped
    "Solar Radiation": "solar_radiation_w_m2",
    "Wind Speed": "wind_speed_ms",
    "Gust Speed": "wind_gust_speed_kmh",  # API returns in m/s actually
    "Wind Direction": "wind_direction_deg",
    "Barometric Pressure": "barometric_pressure_kpa",
}

# Units that need conversion
UNIT_CONVERSIONS: dict[str, dict[str, float]] = {
    "Wind Speed": {"m/s": 3.6},  # multiply to get km/h
    "Gust Speed": {"m/s": 3.6},
}


def _load_devices_json(path: Path) -> dict:
    """Load the devices.json mapping file."""
    with open(path) as f:
        return json.load(f)


def _serial_to_station(devices: dict, serial: str) -> str | None:
    """Look up a station name from a device serial number."""
    for station_name, info in devices.get("stations", {}).items():
        if info.get("device_serial") == serial:
            return station_name
    return None


class JSONAdapter(BaseAdapter):
    """Adapter for Licor Cloud API JSON files."""

    def load(self, path: Path) -> pd.DataFrame:
        """Load a Licor JSON file and return canonical DataFrame."""
        with open(path) as f:
            data = json.load(f)

        # If this is devices.json (metadata), load all sensor data files instead
        if path.name == "devices.json" or "sensors" not in data:
            return self._load_all_sensor_files(path.parent)

        return self._load_single_sensor_file(path, data)

    def _load_single_sensor_file(self, path: Path, data: dict) -> pd.DataFrame:
        """Parse a single Licor sensor data JSON file."""
        # Locate the devices.json file (sibling or parent directory)
        devices_path = path.parent.parent / "devices.json"
        if not devices_path.exists():
            devices_path = path.parent / "devices.json"
        devices: dict = {}
        if devices_path.exists():
            with open(devices_path) as f:
                devices = json.load(f)

        # Infer station from directory name (device serial)
        device_serial = path.parent.name
        station = _serial_to_station(devices, device_serial)

        return self._parse_sensor_data(data, station, path)

    def _load_all_sensor_files(self, base_dir: Path) -> pd.DataFrame:
        """Load all sensor data JSON files from subdirectories of base_dir."""
        devices_path = base_dir / "devices.json"
        devices: dict = {}
        if devices_path.exists():
            with open(devices_path) as f:
                devices = json.load(f)

        frames: list[pd.DataFrame] = []
        for subdir in sorted(base_dir.iterdir()):
            if not subdir.is_dir():
                continue
            for json_file in sorted(subdir.glob("*.json")):
                try:
                    with open(json_file) as f:
                        data = json.load(f)
                    if "sensors" not in data:
                        continue
                    device_serial = subdir.name
                    station = _serial_to_station(devices, device_serial)
                    df = self._parse_sensor_data(data, station, json_file)
                    if len(df) > 0:
                        frames.append(df)
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue

        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    def _parse_sensor_data(
        self, data: dict, station: str | None, path: Path
    ) -> pd.DataFrame:
        """Parse sensor data from a Licor JSON dict."""
        sensors = data.get("sensors", [])
        if isinstance(sensors, dict):
            sensors = [sensors]

        series_map: dict[str, pd.Series] = {}
        for sensor in sensors:
            self._extract_sensor_series(sensor, series_map)

        if not series_map:
            return pd.DataFrame()

        df = pd.DataFrame(series_map)
        df = df.sort_index()
        df.index.name = "timestamp_utc"
        df = df.reset_index()

        if station:
            df["station"] = station
        df["source_file"] = str(path)
        return df

    @staticmethod
    def _extract_sensor_series(
        sensor: dict, series_map: dict[str, pd.Series]
    ) -> None:
        """Extract time-series from a single sensor's data entries."""
        data_entries = sensor.get("data", [])
        if isinstance(data_entries, dict):
            data_entries = [data_entries]

        for entry in data_entries:
            mtype = entry.get("measurementType", "")
            units = entry.get("units", "")
            records = entry.get("records", [])
            if not records:
                continue

            canonical = LICOR_MEASUREMENT_MAP.get(mtype)
            if canonical is None or canonical == "accumulated_rain_mm":
                continue

            ts_vals = JSONAdapter._records_to_series(records)
            if not ts_vals:
                continue

            conv = UNIT_CONVERSIONS.get(mtype, {})
            multiplier = conv.get(units, 1.0)
            s = pd.Series(ts_vals, name=canonical)

            if multiplier != 1.0:
                s = s * multiplier
                if mtype == "Wind Speed" and units == "m/s":
                    s.name = "wind_speed_kmh"
                elif mtype == "Gust Speed" and units == "m/s":
                    s.name = "wind_gust_speed_kmh"

            series_map[s.name] = s

    @staticmethod
    def _records_to_series(
        records: list,
    ) -> dict[pd.Timestamp, float]:
        """Convert raw record pairs [ts_ms, val] to a timestamp dict."""
        ts_vals: dict[pd.Timestamp, float] = {}
        for record in records:
            if len(record) < 2:
                continue
            try:
                ts = pd.Timestamp(record[0], unit="ms", tz="UTC")
                ts_vals[ts] = float(record[1])
            except (ValueError, TypeError):
                continue
        return ts_vals
