# Codemap: `src/pea_met_network/`

> PEA Met Network — Core pipeline, FWI computation, quality enforcement, cross-station imputation, and analysis utilities.
> 20 modules implementing a multi-stage ETL pipeline from raw meteorological data to Fire Weather Index outputs.

---

## Summary Table

| File | Purpose | Key Classes/Functions | Design Pattern |
|---|---|---|---|
| `__init__.py` | Package marker | — | — |
| `__main__.py` | CLI entry point with vmem tuning | `main()` | Facade / Bootstrap |
| `cleaning.py` | Full ETL pipeline orchestrator | `run_pipeline()`, `load_station_files()`, `dedup()`, `resample_hourly()`, `impute()`, `calculate_fwi()`, `aggregate_daily()` | Pipeline, Topological Sort |
| `cross_station_impute.py` | Spatial donor-based gap filling | `DonorAssignment`, `ImputedValue`, `HeightCorrection`, `impute_cross_station()`, `propagate_fwi_quality_flags()` | Strategy, Chain of Responsibility |
| `eccc_api.py` | ECCC MSC GeoMet API client | `EcccStation`, `fetch_eccc_hourly()`, `normalize_eccc_response()` | Client / Cache-aside |
| `fetch_eccc_donors.py` | Standalone ECCC cache pre-populator | `main()` | Script / Batch |
| `fwi.py` | Daily-step FWI moisture codes (Van Wagner) | `fine_fuel_moisture_code()`, `duff_moisture_code()`, `drought_code()`, `initial_spread_index()`, `buildup_index()`, `fire_weather_index()` | Pure Functions |
| `fwi_diagnostics.py` | FWI chain-break detection & reporting | `ChainBreak`, `diagnose_chain_breaks()`, `chain_breaks_to_dataframe()` | Diagnostic / Observer |
| `imputation.py` | Generic configurable gap imputation | `ImputationConfig`, `AuditRecord`, `impute_column()`, `impute_frame()` | Strategy (per-gap-length) |
| `manifest.py` | Raw file discovery & schema recognition | `RawFileRecord`, `SchemaSignature`, `SchemaMatch`, `build_raw_manifest()`, `recognize_schema()` | Registry (pattern matching) |
| `materialize_resampled.py` | Write hourly/daily CSVs from normalized data | `materialize_resampled_outputs()` | Facade / Pipeline terminus |
| `normalized_loader.py` | Load and normalize raw station CSVs | `load_normalized_station_csv()`, `_normalized_name()`, `_parse_timestamp_*()` | Adapter (Schema → Canonical) |
| `qa_qc.py` | QA/QC summary metrics and reports | `missingness_summary()`, `duplicate_timestamps()`, `out_of_range_values()`, `coverage_summary()`, `generate_qa_qc_report()` | Reporting / Aggregation |
| `quality.py` | Enforce data quality rules | `enforce_quality()`, `enforce_fwi_outputs()`, `truncate_date_range()`, `_check_*()` | Strategy (config-driven rules) |
| `redundancy.py` | Station redundancy analysis | `build_station_matrix()`, `pca_station_loadings()`, `cluster_station_order()`, `benchmark_to_stanhope()` | Analysis Pipeline |
| `resampling.py` | Resample to hourly/daily frequencies | `AggregationPolicy`, `resample_hourly()`, `resample_daily()` | Policy / Strategy |
| `stanhope_cache.py` | ECCC Stanhope data fetch/cache | `StanhopeClient`, `StanhopeRequest`, `fetch_stanhope_hourly_month()`, `normalize_stanhope_hourly()` | Client-Server / Cache-Aside |
| `uncertainty.py` | Station removal risk quantification | `quantify_station_removal_risk()` | Statistical Estimation |
| `validation.py` | Station vs reference comparison | `validate_against_reference()`, `compare_station_data()` | Validation / Comparison |
| `vapor_pressure.py` | Vapor pressure & RH derivation | `saturation_vapor_pressure()`, `actual_vapor_pressure()`, `rh_from_vapor_pressure()`, `rh_from_dew_point()` | Stateless Utility |

---

## Pipeline Architecture

```
                          ┌─────────────────────────────────────────────┐
                          │               __main__.py                  │
                          │    (vmem tuning, optional cuDF accel)       │
                          └─────────────────┬───────────────────────────┘
                                            │
                          ┌─────────────────▼───────────────────────────┐
                          │              cleaning.py                     │
                          │           (Pipeline Orchestrator)            │
                          └──┬────┬────┬────┬────┬────┬────┬────┬───────┘
                             │    │    │    │    │    │    │    │
  ┌──────────────────────────┘    │    │    │    │    │    │    └──────────┐
  │                               │    │    │    │    │    │               │
  ▼                               ▼    ▼    ▼    ▼    ▼    ▼               ▼
manifest.py                   adapters  dedup  resample quality impute    aggregate
(discover files)              (load)           .py     .py     .py         .py
                                                      │       │
                                                      │       ▼
                                                      │   cross_station_
                                                      │   impute.py
                                                      │       │
                                                      ▼       ▼
                                                   fwi.py  vapor_pressure.py
                                                      │
                                                      ▼
                                               fwi_diagnostics.py
```

### Pipeline Stages (per station)

1. **Discover** — `manifest.py` scans `data/raw/` for CSV/XLSX/XLE files, infers station/year
2. **Load** — `adapters/` routes by extension, normalizes to canonical DataFrame
3. **Dedup** — `cleaning.py:dedup()` removes exact + timestamp duplicates
4. **Resample** — `resampling.py` resamples to hourly (mean for most, sum for rain)
5. **Truncate** — `quality.py:truncate_date_range()` filters to configured date range
6. **Quality** — `quality.py:enforce_quality()` applies range/rate-of-change/cross-variable/flatline checks
7. **Impute** — `imputation.py` fills short gaps (linear interpolation) with audit trail
8. **Cross-station** — `cross_station_impute.py` fills remaining gaps from donor stations (P1→P2→P3 cascade)
9. **FWI** — `cleaning.py:calculate_fwi()` computes FFMC→DMC→DC→ISI→BUI→FWI chain (hourly iterative)
10. **FWI Quality** — `quality.py:enforce_fwi_outputs()` validates FWI ranges
11. **Chain-break Diagnostics** — `fwi_diagnostics.py` detects FWI continuity breaks
12. **Aggregate** — `cleaning.py:aggregate_daily()` hourly → daily summaries
13. **QA/QC Report** — `qa_qc.py` assembles per-station metrics
14. **Write** — hourly/daily CSVs, imputation report, cross-station audit, QA/QC report

---

## Detailed Per-File Documentation

### `__init__.py`

**Purpose:** Package marker; declares `pea_met_network` as a Python package.

**Integration Points:** Imported implicitly when `pea_met_network` is referenced.

---

### `__main__.py`

**Purpose:** Enables `python -m pea_met_network` invocation, raising the virtual memory ceiling before launching the cleaning pipeline.

**Key Classes/Functions:**
- `main()` — Conditionally activates cuDF.pandas acceleration (via `PEA_CUDF=1` env var), then delegates to `cleaning.main()`.

**Design Patterns:** Bootstrap / Facade — thin entry point that handles environment setup before invoking the real pipeline.

**Data Flow:** CLI args → `cleaning.main()`.

**Integration Points:** Imports `cleaning.main`.

---

### `cleaning.py`

**Purpose:** Core ETL pipeline orchestrator — discovers raw files, loads via adapters, cleans, imputes, computes FWI, and writes all outputs.

**Key Classes/Functions:**
- `run_pipeline(stations, force)` — Master pipeline with topological station ordering and per-station serial processing.
- `main()` — CLI argument parser (`--stations`, `--force`, `--dry-run`).
- `load_donor_config(config)` — Parses `cleaning-config.json` into `DonorAssignment` objects.
- `_topological_station_order(stations, donor_assignments)` — Kahn's algorithm for donor→target ordering.
- `load_station_files(station_files, station)` — Loads raw files via `adapters.registry.route_by_extension`.
- `dedup(df)` — Removes exact + timestamp duplicates.
- `resample_hourly(df)` — Resamples to hourly frequency.
- `impute(df, station, max_gap_hours)` — Linear interpolation for short gaps.
- `calculate_fwi(df, gap_threshold_hours)` — Full FWI system with hourly iterative chain and gap-aware restart.
- `aggregate_daily(hourly_df)` — Aggregates hourly to daily.
- `should_process(station, force)` — Checks if output is stale relative to inputs.
- `_save_donor_parquet()` / `_load_donor_from_disk()` — Disk-based donor staging via Parquet.

**Design Patterns:** Pipeline, Topological Sort (Kahn's), Cache-aside (disk staging), Lazy evaluation.

**Data Flow:**
- **In:** Raw files in `data/raw/`, `cleaning-config.json`.
- **Out:** `data/processed/{station}/station_hourly.csv`, `station_daily.csv`; reports (imputation, QA/QC, cross-station audit, quality enforcement, FWI missingness).

**Integration Points:**
- Imports: `adapters.registry`, `cross_station_impute`, `fwi_diagnostics`, `qa_qc`, `quality`, `vapor_pressure`.

---

### `cross_station_impute.py`

**Purpose:** Fills missing meteorological variables using spatial transfer from donor stations with full audit trail.

**Key Classes/Functions:**
- `DonorAssignment` (frozen dataclass) — Maps target station + variable → donor station with priority and type.
- `HeightCorrection` (frozen dataclass) — Wind speed height correction parameters.
- `ImputedValue` (dataclass) — Single imputed-value audit record.
- `impute_cross_station(target_df, station, donor_assignments, ...)` — Main function: tries donors by priority (P1→P2→P3).
- `_rh_from_donor()` — RH derivation via Td+T (ECCC) or VP continuity (internal).
- `_transfer_wind()` — Wind speed with optional power-law height scaling.
- `_transfer_temp()` — Temperature spatial proxy with asymmetric outlier guard.
- `derive_height_correction_factor()` — Empirically derives wind height correction from overlapping data.
- `propagate_fwi_quality_flags(df)` — Propagates max input quality flag to FWI outputs.

**Design Patterns:** Chain of Responsibility (donor cascade), Strategy (per-variable transfer), Audit Trail.

**Data Flow:** Target station hourly DF + donor configs → augmented DF + audit records.

**Integration Points:**
- Imports: `vapor_pressure`, `eccc_api.ECCC_CACHE_KEY_MAP`.
- Called by: `cleaning.py`.

---

### `eccc_api.py`

**Purpose:** Client for Environment and Climate Change Canada MSC GeoMet API to fetch hourly climate observations.

**Key Classes/Functions:**
- `EcccStation` (frozen dataclass) — Station metadata: climate_id, stn_id, name, local_tz, anemometer_height_m.
- `ECCC_DONOR_STATIONS` (dict) — Registry of 3 donor stations.
- `fetch_eccc_hourly(station, start, end, *, limit, cache_dir, force)` — Fetches with pagination, caches to CSV.
- `normalize_eccc_response(features, station_name, local_tz)` — GeoJSON → canonical DataFrame.

**Design Patterns:** Client, Cache-aside, Data Normalization.

**Data Flow:** API URL → normalized DataFrame (cached CSV + provenance.json).

**Integration Points:**
- Called by: `fetch_eccc_donors.py`, `cross_station_impute.py`.

---

### `fetch_eccc_donors.py`

**Purpose:** Standalone CLI script to pre-populate the ECCC donor cache.

**Key Classes/Functions:**
- `main()` — Iterates `ECCC_DONOR_STATIONS` and calls `fetch_eccc_hourly()`.

**Design Patterns:** Batch Script.

**Integration Points:** Imports `eccc_api`.

---

### `fwi.py`

**Purpose:** Daily-step Canadian Fire Weather Index (FWI) moisture code calculations following Van Wagner (1987).

**Key Classes/Functions:**
- `fine_fuel_moisture_code(temp, rh, wind, rain, ffmc0)` — Daily FFMC computation.
- `duff_moisture_code(temp, rh, rain, dmc0, month, lat)` — Daily DMC with day-length factors.
- `drought_code(temp, rain, dc0, month, lat)` — Daily DC with day-length adjustment.
- `initial_spread_index(ffmc, wind)` — ISI from FFMC and wind speed.
- `buildup_index(dmc, dc)` — BUI from DMC and DC.
- `fire_weather_index(isi, bui)` — Final FWI from ISI and BUI.

**Design Patterns:** Pure Functions, Reference Implementation.

**Data Flow:** Scalar weather inputs + previous day's codes → scalar FWI component values.

**Integration Points:** Standalone reference; main pipeline uses inline FWI in `cleaning.py`.

---

### `fwi_diagnostics.py`

**Purpose:** Detects and reports FWI state-chain breaks where iterative moisture codes lose continuity.

**Key Classes/Functions:**
- `ChainBreak` (dataclass) — Single chain-break event with station, code, timestamps, cause.
- `diagnose_chain_breaks(hourly_df, station, quality_actions)` — Scans FWI columns for NaN regions, correlates with quality enforcement.
- `chain_breaks_to_dataframe(breaks)` — Converts to tabular DataFrame.

**Design Patterns:** Diagnostic / Observer.

**Data Flow:** Hourly DF + quality actions → `ChainBreak` list / DataFrame.

**Integration Points:** Called by `cleaning.py`.

---

### `imputation.py`

**Purpose:** Generic, configurable gap imputation engine with full audit trail.

**Key Classes/Functions:**
- `ImputationConfig` (frozen dataclass) — Configurable gap-length thresholds and strategies.
- `AuditRecord` (frozen dataclass) — Single imputation audit entry.
- `impute_column(series, config)` — Imputes a single Series with gap-length-aware strategies.
- `impute_frame(frame, variables, config, station_column)` — Multi-variable imputation.

**Design Patterns:** Strategy (per gap-length), Audit Trail, Per-station Grouping.

**Data Flow:** Series/DataFrame → imputed Series/DataFrame + audit records.

---

### `manifest.py`

**Purpose:** Discovers raw data files, infers station/year metadata, and recognizes column schemas.

**Key Classes/Functions:**
- `RawFileRecord` (frozen dataclass) — Discovered raw file metadata.
- `SchemaSignature` (frozen dataclass) — Column schema fingerprint.
- `SchemaMatch` (dataclass) — Schema family name + signature.
- `build_raw_manifest(base_dir)` — Scans `data/raw/` for files with inferred metadata.
- `recognize_schema(columns)` — Classifies into schema families (legacy_dual_wind, hoboware, minimal, single_timestamp).

**Design Patterns:** Registry, Pattern Recognition, Data Class Hierarchy.

---

### `materialize_resampled.py`

**Purpose:** End-to-end convenience function that loads, resamples, and writes hourly/daily CSVs.

**Key Classes/Functions:**
- `materialize_resampled_outputs(source_path, station, output_dir)` — Load → resample → write.

**Design Patterns:** Facade / Pipeline terminus.

**Integration Points:** Imports `normalized_loader`, `resampling`.

---

### `normalized_loader.py`

**Purpose:** Read a raw station CSV, detect schema, rename columns, coalesce duplicates, parse timestamps, return canonical DataFrame.

**Key Classes/Functions:**
- `COLUMN_RENAMES` — Mapping from raw column names to canonical internal names.
- `load_normalized_station_csv(path, station)` — Full load → rename → coalesce → parse pipeline.

**Design Patterns:** Adapter, Strategy (implicit timestamp parsing dispatch).

**Integration Points:** Imports `column_maps`, `manifest.recognize_schema`. Called by `materialize_resampled.py`, `cleaning.py`.

---

### `qa_qc.py`

**Purpose:** Compute per-station QA/QC metrics and assemble comprehensive reports.

**Key Classes/Functions:**
- `missingness_summary(df)` — Per-variable missing count & percentage.
- `duplicate_timestamps(df)` — Duplicate timestamp detection.
- `out_of_range_values(df, ranges)` — Physical bounds checking.
- `generate_qa_qc_report(hourly, daily, quality_actions, chain_breaks)` — Full per-station report.

**Design Patterns:** Reporter / Aggregator.

**Data Flow:** Hourly + daily DataFrames → summary DataFrame (~20 columns per station).

---

### `quality.py`

**Purpose:** Enforce data quality rules — value ranges, rate-of-change, cross-variable, flatline — with configurable actions.

**Key Classes/Functions:**
- `enforce_quality(df, config)` — Runs all four check types, returns `(cleaned_df, actions)`.
- `enforce_fwi_outputs(df, config)` — Validates FWI output columns.
- `truncate_date_range(df, config)` — Filters rows before configured start date.
- `_check_value_ranges()`, `_check_rate_of_change()`, `_check_cross_variable()`, `_check_flatline()` — Individual rule checkers.

**Design Patterns:** Strategy (config-driven rules), Collecting Parameter (flag_map), Command (action records).

**Data Flow:** DataFrame + config → cleaned DataFrame + action log.

---

### `redundancy.py`

**Purpose:** Analyze station redundancy via correlation, PCA, hierarchical clustering, and Stanhope benchmarking.

**Key Classes/Functions:**
- `build_station_matrix()` — Pivot to station×timestamp matrix.
- `pca_station_loadings()` — PCA analysis of station patterns.
- `cluster_station_order()` — Agglomerative clustering for station grouping.
- `benchmark_to_stanhope()` — Per-station comparison against Stanhope reference.
- `build_station_recommendations()` — Synthesizes evidence → keep/remove/defer.
- `write_redundancy_summary()` — Full pipeline → Markdown report.

**Design Patterns:** Analysis Pipeline, Composite Evidence.

**Integration Points:** Imports `uncertainty`, `sklearn`. Standalone analysis module.

---

### `resampling.py`

**Purpose:** Resample normalized DataFrames to hourly or daily frequencies with configurable per-variable aggregation.

**Key Classes/Functions:**
- `AggregationPolicy` (frozen dataclass) — Maps variables to aggregation methods.
- `resample_normalized_frame(frame, frequency, policy)` — Core resampling algorithm.
- `resample_hourly()`, `resample_daily()` — Convenience wrappers.

**Design Patterns:** Policy, Template Method.

**Integration Points:** Called by `cleaning.py`, `materialize_resampled.py`.

---

### `stanhope_cache.py`

**Purpose:** Download ECCC Stanhope hourly weather data month-by-month, cache to disk with provenance tracking.

**Key Classes/Functions:**
- `StanhopeRequest` (frozen dataclass) — Value object for year/month requests.
- `StanhopeClient` — HTTP fetch abstraction (injectable for testing).
- `fetch_stanhope_hourly_month()` — Fetch one month with cache check.
- `normalize_stanhope_hourly()` — Cached CSV → canonical DataFrame.

**Design Patterns:** Client-Server, Cache-Aside, Provenance Tracking.

---

### `uncertainty.py`

**Purpose:** Quantify risk of station removal using KDE-based uncertainty estimation.

**Key Classes/Functions:**
- `quantify_station_removal_risk(benchmark)` — Per-station risk → DataFrame with probability, CI, band.

**Design Patterns:** Statistical Estimation, Fallback Strategy.

**Integration Points:** Called by `redundancy.build_station_recommendations`. Imports `scipy.stats`.

---

### `validation.py`

**Purpose:** Compare local PEINP station data against the ECCC Stanhope reference station.

**Key Classes/Functions:**
- `validate_against_reference(station, reference_df, station_df)` — Overlap + mean absolute diff per FWI column.
- `compare_station_data(ref_df, cmp_df, on, value_cols)` — Inner-merge comparison.

**Design Patterns:** Validation / Comparison.

---

### `vapor_pressure.py`

**Purpose:** Pure-math vapor pressure and relative humidity derivation using August-Roche-Magnus formula.

**Key Classes/Functions:**
- `saturation_vapor_pressure(temp_c)` — ARM formula → kPa.
- `actual_vapor_pressure(temp_c, rh_pct)` — `e = (RH/100) * es(T)`.
- `rh_from_vapor_pressure(temp_c, vp_kpa)` — Inverse ARM, capped at 100%.
- `rh_from_dew_point(temp_c, dew_point_c)` — Preferred method for ECCC donors (0.1°C precision).

**Design Patterns:** Stateless Utility, Precision Hierarchy.

**Data Flow:** numpy arrays (temp, RH, dew point) → numpy arrays (vapor pressure, RH).

**Integration Points:** Called by `cross_station_impute.py`. Imports `numpy` only.
