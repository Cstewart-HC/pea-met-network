# src/pea_met_network/

## Responsibility
Core data processing library for the PEA meteorological network. Provides end-to-end pipeline from raw CSV ingestion through FWI computation, redundancy analysis, and uncertainty estimation.

## Module Map

| Module | Responsibility | Key Functions/Classes | Dependencies |
|--------|----------------|----------------------|--------------|
| `manifest.py` | File discovery, station inference, schema recognition | `build_raw_manifest()`, `recognize_schema()`, `infer_station()`, `infer_year()` | None (stdlib only) |
| `normalized_loader.py` | CSV ingestion, column renaming, timestamp parsing | `load_normalized_station_csv()` | `manifest.py` (schema recognition) |
| `resampling.py` | Hourly/daily aggregation with configurable policies | `resample_hourly()`, `resample_daily()`, `AggregationPolicy` | None (pandas) |
| `materialize_resampled.py` | Write resampled outputs to disk | `materialize_resampled_outputs()` | `normalized_loader.py`, `resampling.py` |
| `fwi.py` | Canadian Fire Weather Index system (Van Wagner 1987) | `fine_fuel_moisture_code()`, `duff_moisture_code()`, `drought_code()`, `initial_spread_index()`, `buildup_index()`, `fire_weather_index()` | None (math only) |
| `stanhope_cache.py` | ECCC Stanhope reference station data download + cache | `fetch_stanhope_hourly_month()`, `materialize_stanhope_hourly_range()`, `StanhopeClient` | None (urllib) |
| `imputation.py` | Conservative gap-filling with audit trail | `impute_column()`, `impute_frame()`, `audit_trail_to_dataframe()`, `ImputationConfig` | None (pandas) |
| `qa_qc.py` | Data quality checks | `missingness_summary()`, `duplicate_timestamps()`, `out_of_range_values()`, `coverage_summary()` | None (pandas) |
| `redundancy.py` | Station redundancy analysis | `build_station_matrix()`, `pca_station_loadings()`, `cluster_station_order()`, `benchmark_to_stanhope()`, `build_station_recommendations()`, `write_redundancy_summary()` | `uncertainty.py`, sklearn |
| `uncertainty.py` | KDE-based station removal risk estimation | `quantify_station_removal_risk()` | scipy, numpy |

## Data Flow
1. **Ingest**: `manifest.py` discovers raw files → `normalized_loader.py` loads and normalizes
2. **Quality**: `qa_qc.py` checks for missingness, duplicates, out-of-range values
3. **Impute**: `imputation.py` fills short gaps, preserves long gaps, produces audit trail
4. **Resample**: `resampling.py` aggregates to hourly/daily frequencies
5. **FWI**: `fwi.py` computes moisture codes (FFMC, DMC, DC) and indices (ISI, BUI, FWI) sequentially
6. **Redundancy**: `redundancy.py` runs PCA, clustering, and benchmarking against Stanhope reference
7. **Uncertainty**: `uncertainty.py` estimates risk probabilities via KDE over station-reference divergence

## Integration Points
- **Consumed by**: `cleaning.py` (root entrypoint), `tests/` (verification), `notebooks/analysis.ipynb` (analysis)
- **Depends on**: `pandas`, `numpy`, `scipy`, `sklearn` (for PCA/clustering)
- **External data**: `data/raw/peinp/` (station CSVs), ECCC WeatherCAN API (Stanhope reference)
