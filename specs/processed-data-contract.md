# Processed Data Contract

## Scope
This contract defines the first processed outputs produced from normalized
station telemetry during Phase 2 (Scrub): hourly and daily station-level
resampled datasets.

## Input assumptions
- input records are already normalized to one row per observation timestamp
- `timestamp_utc` is timezone-aware and stored in UTC
- `station` is a canonical station key such as `cavendish` or `greenwich`
- each measurement column uses normalized names and explicit units

## Output datasets
Two processed datasets are expected:
- `station_hourly.*` for hourly left-labeled UTC buckets
- `station_daily.*` for daily left-labeled UTC buckets

File format is intentionally open for now. CSV or parquet are both acceptable
as long as the column contract stays stable.

## Required columns
Every processed dataset must include, in this order:
1. `station`
2. `timestamp_utc`
3. normalized measurement columns in deterministic order

## Aggregation rules
- mean: `air_temperature_c`, `relative_humidity_pct`, `dew_point_c`,
  `wind_speed_kmh`, `wind_speed_ms`, `wind_gust_speed_kmh`,
  `solar_radiation_w_m2`, `battery_v`
- sum: `rain_mm`
- max: `wind_gust_speed_max_kmh`
- first: `wind_direction_deg`

Unknown normalized variables are not allowed to silently pass through. They must
trigger an explicit rule decision first.

## Time bucketing
- hourly uses UTC `1h` buckets
- daily uses UTC `1D` buckets
- buckets are left-closed and left-labeled
- station grouping happens before resampling

## Metadata handling
Raw provenance columns such as `source_file` and `schema_family` are validation
inputs but are excluded from aggregated processed outputs in the current phase.

## Validation expectations
- no duplicate `station` + `timestamp_utc` keys in processed outputs
- no missing required identifier columns
- UTC timezone must remain intact after resampling
- processed outputs must be reproducible from the same normalized inputs
