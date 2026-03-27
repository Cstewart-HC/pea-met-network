# Repository Atlas: pea-met-network

## Project Responsibility
Autonomous weather station data pipeline for the PEI meteorological network.
Ingests raw station telemetry from multiple sources (PEINP CSVs, XLSX, XLE,
Licor Cloud JSON, ECCC API), normalizes schemas via format adapters, resamples
to hourly/daily, imputes gaps, and computes Fire Weather Index (FWI) system
metrics. Stanhope serves as the ECCC validation reference.

## System Entry Points
- `src/pea_met_network/__main__.py`: CLI entry point — `python -m pea_met_network --stations all [--force] [--dry-run]`
- `src/pea_met_network/cleaning.py`: Pipeline orchestrator — discovers ALL raw data files, routes each through its format adapter, concatenates per station, deduplicates, resamples, imputes, computes FWI, generates QA/QC, and writes outputs.
- `scripts/sync_state.py`: State machine operator — manages phase transitions, verdict validation, circuit breaker, and auto-commit.
- `scripts/record_verdict.py`: Deterministic verdict recording — captures HEAD, updates `validation.json`, commits.

## Directory Map

| Directory | Responsibility | Detailed Map |
|-----------|----------------|--------------|
| `src/pea_met_network/` | Core library — adapters, pipeline, normalization, resampling, FWI, imputation, QA/QC, validation | [View Map](src/pea_met_network/codemap.md) |
| `src/pea_met_network/adapters/` | Format adapters — csv, xlsx, xle, json — Strategy pattern with registry-based factory | [View Map](src/pea_met_network/adapters/codemap.md) |
| `scripts/` | Infrastructure — state machine, verdict recording | — |
| `tests/` | Test suite — acceptance criteria verification per phase | — |
| `specs/` | Pipeline rebuild specs (v2 — 8 phases) | — |
| `docs/` | Loop prompts, state files, validation, diary, archive | — |
| `notebooks/` | Analysis notebook (from v1 project) | — |
| `data/raw/` | Raw data — PEINP CSVs/XLSX/XLE, Licor JSONs, Stanhope cache | — |
| `data/processed/` | Pipeline output — hourly/daily CSVs, FWI, reports (gitignored) | — |

## Data Flow (v2 — Adapter Architecture)

```
                  CLI: python -m pea_met_network
                          │
                  cleaning.py:main()
                          │
                  discover_raw_files()
                  (csv, xlsx, xle, json)
                          │
        ┌─────────────────┼─────────────────┬─────────────────┐
        ▼                 ▼                 ▼                 ▼
   csv_adapter       xlsx_adapter       xle_adapter      json_adapter
   (PEINP + ECCC)   (HOBOware XLSX)   (Solinst XML)    (Licor Cloud)
        │                 │                 │                 │
        └─────────────────┴─────────────────┴─────────────────┘
                          │
                   canonical DataFrame
                   (single exit schema)
                          │
                  concat per station
                          │
                   dedup timestamps
                          │
            resampling.py ─── hourly (1h UTC) + daily (1D UTC)
                          │
            imputation.py ─── conservative gap-filling + audit
                          │
            fwi.py ──────── FFMC → DMC → DC → ISI → BUI → FWI
                          │
            qa_qc.py ───── missingness, duplicates, out-of-range
                          │
            validation.py ─ Stanhope cross-validation
                          │
            data/processed/<station>/station_{hourly,daily}.csv
            data/processed/imputation_report.csv
            data/processed/qa_qc_report.csv
            data/processed/pipeline_manifest.json
```

## Module Map

| Module | Responsibility | Key Functions |
|--------|----------------|---------------|
| `cleaning.py` | Full pipeline orchestrator | `discover_raw_files()`, `load_all_files()`, `dedup()`, `resample_hourly()`, `impute()`, `calculate_fwi()`, `aggregate_daily()`, `run_pipeline()`, `main()` |
| `validation.py` | Stanhope cross-validation | `compare_station_data()`, `validate_against_reference()` |
| `adapters/__init__.py` | Adapter registry + router | `route_by_extension()`, `load_file()` |
| `adapters/csv_adapter.py` | PEINP CSV + ECCC Stanhope CSV | `CSVAdapter.load()` |
| `adapters/xlsx_adapter.py` | HOBOware XLSX (Greenwich 2023) | `XLSXAdapter.load()` |
| `adapters/xle_adapter.py` | Solinst XLE XML (Stanley Bridge 2022) | `XLEAdapter.load()` |
| `adapters/json_adapter.py` | Licor Cloud API JSON | `JSONAdapter.load()` |
| `adapters/column_maps.py` | Shared column rename mappings | `rename_columns()`, `derive_wind_speed_kmh()` |
| `adapters/schema.py` | Canonical schema definition | `CANONICAL_SCHEMA` |
| `adapters/registry.py` | Extension-to-adapter routing | `ADAPTER_REGISTRY`, `route_by_extension()` |
| `manifest.py` | File discovery (all formats) | `build_raw_manifest()`, `recognize_schema()` |
| `normalized_loader.py` | Legacy CSV ingestion (used by csv_adapter) | `load_normalized_station_csv()` |
| `resampling.py` | Hourly/daily aggregation | `resample_hourly()`, `resample_daily()`, `AggregationPolicy` |
| `fwi.py` | Canadian FWI system (Van Wagner 1987) | `fine_fuel_moisture_code()`, `duff_moisture_code()`, `drought_code()`, `initial_spread_index()`, `buildup_index()`, `fire_weather_index()` |
| `stanhope_cache.py` | ECCC Stanhope download + cache | `fetch_stanhope_hourly_month()`, `materialize_stanhope_hourly_range()`, `normalize_stanhope_hourly()` |
| `imputation.py` | Conservative gap-filling | `impute_column()`, `impute_frame()`, `audit_trail_to_dataframe()` |
| `qa_qc.py` | Data quality checks | `missingness_summary()`, `duplicate_timestamps()`, `out_of_range_values()`, `coverage_summary()`, `generate_qa_qc_report()` |
| `redundancy.py` | Station redundancy analysis | `build_station_matrix()`, `pca_station_loadings()`, `cluster_station_order()`, `benchmark_to_stanhope()` |
| `uncertainty.py` | KDE-based station removal risk estimation | `quantify_station_removal_risk()` |

## Canonical Output Schema

Every adapter produces a DataFrame with these columns:

| Column | Type | Required for FWI | Hourly Aggregation |
|--------|------|-------------------|--------------------|
| station | str | — | first |
| timestamp_utc | datetime64[ns, UTC] | — | — |
| air_temperature_c | float | ✅ | mean |
| relative_humidity_pct | float | ✅ | mean |
| wind_speed_kmh | float | ✅ | mean |
| wind_direction_deg | float | — | first |
| wind_gust_speed_kmh | float | — | max |
| rain_mm | float | ✅ | sum |
| dew_point_c | float | — | mean |
| solar_radiation_w_m2 | float | — | mean |
| barometric_pressure_kpa | float | — | mean |
| water_level_m | float | — | mean |
| water_pressure_kpa | float | — | mean |
| water_temperature_c | float | — | mean |

## Key Design Decisions (v2)

- **Adapter architecture** — single entry point (`cleaning.py`), format adapters (csv/xlsx/xle/json) using Strategy pattern, canonical output schema. Unknown formats are HARD ERRORS, never silently skipped.
- **Pipeline lives in `cleaning.py`** — the full orchestration (including FWI calculation and imputation) is self-contained in `cleaning.py`. Standalone modules (`fwi.py`, `imputation.py`) exist for direct use outside the pipeline.
- **`python -m pea_met_network`** — enabled via `__main__.py`, delegates to `cleaning.main()`.
- **Pipeline manifest with checksums** — SHA256 checksums for all output artifacts, enabling determinism verification.
- **No data gaps by construction** — every file in `data/raw/` is discovered, routed, and processed. The manifest reports 0 unprocessed files.
- **Serial, pandas, single-process** — ~150K total rows, no parallelism needed.
- **8 phases** — adapter refactor → format coverage → imputation → Stanhope validation → QA/QC → determinism → Licor JSON → E2E validation.
- **Stanhope is first-class** — daily output + FWI + cross-validation against Greenwich.
- **Licor JSON is just another adapter** — no separate code path, no deferred phase.

## Archive
- `docs/archive/v1-project-complete.zip` — all v1 specs, MISS-HOOVER-PATTERN.md, data audit inventory
- `docs/archive/phases.md`, `docs/archive/status.md` — v1 phase history
