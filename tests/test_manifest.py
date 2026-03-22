from pathlib import Path

from pea_met_network.manifest import build_raw_manifest, recognize_schema


def test_build_raw_manifest_finds_expected_station() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    records = build_raw_manifest(base_dir)

    assert records
    stations = {record.station for record in records}
    assert "cavendish" in stations
    assert "greenwich" in stations
    assert "tracadie" in stations


def test_build_raw_manifest_sets_year_for_station_csvs() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    records = build_raw_manifest(base_dir)

    sample = next(record for record in records if record.station == "cavendish")
    assert sample.year in {2022, 2023, 2024, 2025}


def test_recognize_schema_for_hoboware_date_time_family() -> None:
    columns = [
        "Date",
        "Time",
        "Temperature (S-TMB 21038195:21098956-1),°C,Cavendish",
        "Relative Humidity,%,Cavendish",
        "Average wind speed (S-WCF 21038195:21038454-1),Km/h,Cavendish",
        "Rain (S-RGB 21038195:21038368-1),mm,Cavendish",
    ]

    match = recognize_schema(columns)

    assert match.family == "minimal_date_time_family"
    assert match.signature.has_temperature is True
    assert match.signature.has_relative_humidity is True
    assert match.signature.has_wind_speed is True
    assert match.signature.has_rain is True


def test_recognize_schema_for_legacy_dual_wind_family() -> None:
    columns = ["Date", "Time"] + [f"col_{i}" for i in range(19)]

    match = recognize_schema(columns)

    assert match.family == "legacy_dual_wind_family"
    assert match.signature.column_count == 21
