# Phase 11 — Dual-Mode FWI Pipeline (Compliant + Extended)

## Objective

Add a compliant FWI calculation mode alongside the existing extended (hourly) mode. The compliant mode follows Van Wagner (1987) — one row per day at local noon observation time. The extended mode remains unchanged.

## Requirements

### 11.1 CLI & Config

- Add `--fwi-mode` CLI argument to `__main__.py`: `extended` (default) | `compliant`
- Add `"fwi_mode": "extended"` to `docs/cleaning-config.json` under an `"fwi"` section
- Default latitude: `46.4` (PEI). Code must accept per-station latitude override via config (future-proof)

### 11.2 Noon Observation Filter

- New function `filter_noon_observations(df: pd.DataFrame) -> pd.DataFrame`
- Input: hourly DataFrame with `timestamp_utc` column
- Filter to local noon (12:00 ADT = 15:00 UTC, 12:00 AST = 16:00 UTC)
- Use `zoneinfo.ZoneInfo("America/Halifax")` for DST-aware localization — no new dependencies
- Sum `rain_mm` over the preceding 24h window (not just the noon hour)
- Output: one row per date with temp, RH, wind at noon + 24h rain total

### 11.3 Daily FWI Calculation

- New function `calculate_fwi_daily(df: pd.DataFrame, lat: float = 46.4) -> pd.DataFrame`
- Uses existing `fwi.py` single-step Van Wagner functions (NOT the hourly iterative versions in `cleaning.py`):
  - `fine_fuel_moisture_code(temp, rh, wind, rain, ffmc0)`
  - `duff_moisture_code(temp, rh, rain, dmc0, month, lat)`
  - `drought_code(temp, rain, dc0, month, lat)`
  - `initial_spread_index(ffmc, wind)`
  - `buildup_index(dmc, dc)`
  - `fire_weather_index(isi, bui)`
- Missing noon observation → carry forward previous day's FWI codes (Van Wagner standard)
- Missing rain → treat as 0.0 mm (Van Wagner standard)
- Initialize first day from FWI startup table values (FFMC=85, DMC=6, DC=15)

### 11.4 Pipeline Routing

- In `run_pipeline()`, after cross-station imputation, branch on `fwi_mode`:
  - `extended`: existing `calculate_fwi()` → `aggregate_daily()` (UNCHANGED)
  - `compliant`: `filter_noon_observations()` → `calculate_fwi_daily()` → write `data/processed/{station}_daily_compliant.csv`
- Compliant mode still writes hourly data (without FWI columns) for reference
- Daily output filename: `{station}_daily_compliant.csv`

### 11.5 Diagnostics

- In compliant mode, report days where carry-forward was used (data quality signal)
- Chain breaks should be near-zero — carry-forward eliminates cascading NaN
- Log the count of carry-forward days per station

### 11.6 Tests

- Test noon filter produces correct local-time rows for both ADT and AST periods
- Test 24h rain sum correctness
- Test daily FWI loop against known Van Wagner test vectors (use existing `test_fwi_vectors.py`)
- Test carry-forward on missing days
- Test default latitude (46.4) and per-station override
- Test CLI `--fwi-mode compliant` flag
- End-to-end test for one station in compliant mode

## Constraints

- Do NOT modify existing extended (hourly) FWI calculation
- Do NOT modify `fwi.py` — the reference implementation is correct as-is
- Do NOT add new dependencies — use `zoneinfo` from stdlib
- Do NOT change output filenames for extended mode
- All new code must pass ruff lint

## Exit Gate

```bash
pytest tests/ -m 'not e2e' -v
```

All existing tests pass + new Phase 11 tests pass.
