# src/pea_met_network/

## Responsibility
Core data processing library for the PEA meteorological network. Provides end-to-end pipeline from raw file discovery through FWI computation, imputation, QA/QC reporting, and Stanhope cross-validation.

## Module Map

| Module | Responsibility | Key Functions/Classes | Dependencies |
|--------|----------------|----------------------|--------------|
| `__init__.py` | Package initialization | Public API surface | — |
| `__main__.py` | CLI entry point for `python -m pea_met_network` | `main()` — delegates to `cleaning.main()` | `cleaning` |
| `cleaning.py` | Full pipeline orchestrator | `discover_raw_files()`, `load_all_files()`, `dedup()`, `resample_hourly()`, `impute()`, `calculate_fwi()`, `aggregate_daily()`, `run_pipeline()`, `main()` | `adapters.registry`, `qa_qc` |
| `validation.py` | Stanhope cross-validation utilities | `compare_station_data()`, `validate_against_reference()` | pandas |
| `manifest.py` | File discovery, station inference, schema recognition | `build_raw_manifest()`, `recognize_schema()`, `infer_station()`, `infer_year()` | None (stdlib only) |
| `normalized_loader.py` | CSV ingestion, column renaming, timestamp parsing | `load_normalized_station_csv()` | `manifest.py` (schema recognition) |
| `resampling.py` | Hourly/daily aggregation with configurable policies | `resample_hourly()`, `resample_daily()`, `AggregationPolicy` | None (pandas) |
| `materialize_resampled.py` | Write resampled outputs to disk | `materialize_resampled_outputs()` | `normalized_loader.py`, `resampling.py` |
| `fwi.py` | Canadian Fire Weather Index system (Van Wagner 1987) | `fine_fuel_moisture_code()`, `duff_moisture_code()`, `drought_code()`, `initial_spread_index()`, `buildup_index()`, `fire_weather_index()` | None (math only) |
| `stanhope_cache.py` | ECCC Stanhope reference station data download + cache | `fetch_stanhope_hourly_month()`, `materialize_stanhope_hourly_range()`, `StanhopeClient`, `normalize_stanhope_hourly()` | None (urllib) |
| `imputation.py` | Conservative gap-filling with audit trail | `impute_column()`, `impute_frame()`, `audit_trail_to_dataframe()`, `ImputationConfig` | None (pandas) |
| `qa_qc.py` | Data quality checks and report generation | `missingness_summary()`, `duplicate_timestamps()`, `out_of_range_values()`, `coverage_summary()`, `calculate_completeness()`, `generate_qa_qc_report()` | None (pandas) |
| `redundancy.py` | Station redundancy analysis | `build_station_matrix()`, `pca_station_loadings()`, `cluster_station_order()`, `benchmark_to_stanhope()`, `build_station_recommendations()`, `write_redundancy_summary()` | `uncertainty.py`, sklearn |
| `uncertainty.py` | KDE-based station removal risk estimation | `quantify_station_removal_risk()` | scipy, numpy |
| `adapters/` | Format adapter layer (Strategy pattern) | `BaseAdapter`, `route_by_extension()`, CSV/XLSX/XLE/JSON adapters | pandas, openpyxl, defusedxml |

## Data Flow
1. **Discover**: `cleaning.discover_raw_files()` scans `data/raw/` (PEINP, ECCC, Licor)
2. **Load**: `adapters.route_by_extension()` dispatches to format-specific adapters → canonical DataFrame
3. **Dedup**: `cleaning.dedup()` removes exact and timestamp duplicates
4. **Resample**: `cleaning.resample_hourly()` aggregates to hourly frequency (mean for measurements, sum for rain)
5. **Impute**: `cleaning.impute()` fills short gaps (≤6h) via linear interpolation, preserves longer gaps
6. **FWI**: `cleaning.calculate_fwi()` computes FFMC → DMC → DC → ISI → BUI → FWI (Van Wagner 1987)
7. **Aggregate**: `cleaning.aggregate_daily()` rolls hourly to daily summaries
8. **QA/QC**: `qa_qc.generate_qa_qc_report()` produces per-station quality metrics
9. **Validate**: `validation.validate_against_reference()` cross-compares stations vs Stanhope ECCC reference
10. **Write**: hourly/daily CSVs, imputation report, QA/QC report, pipeline manifest (with SHA256 checksums)

## Integration Points
- **Consumed by**: `tests/` (verification), `notebooks/analysis.ipynb` (analysis)
- **CLI entry**: `python -m pea_met_network --stations all [--force] [--dry-run]`
- **Depends on**: `pandas`, `numpy`, `scipy`, `sklearn` (for PCA/clustering), `openpyxl`, `defusedxml`
- **External data**: `data/raw/peinp/` (station CSVs/XLSX/XLE), `data/raw/eccc/stanhope/` (ECCC CSVs), `data/raw/licor/` (Licor JSON), ECCC WeatherCAN API (Stanhope reference)

## Key Design Decisions
- **Adapter architecture**: single entry point (`cleaning.py`), format adapters (csv/xlsx/xle/json), canonical output schema. Unknown formats are HARD ERRORS.
- **Cleaning.py as monolith pipeline**: `cleaning.py` contains the full orchestration, FWI calculation, and imputation logic (not delegated to separate modules like `fwi.py` or `imputation.py`). The standalone modules (`fwi.py`, `imputation.py`) remain for direct use outside the pipeline.
- **`__main__.py`** enables `python -m pea_met_network` invocation, delegating to `cleaning.main()`.
- **Pipeline manifest**: SHA256 checksums for all output artifacts, enabling determinism verification.
- **Serial, pandas, single-process**: ~150K total rows, no parallelism needed.
