# FWI Forecast Pipeline — Implementation Plan

## Branch
`feat/fwi-prediction-from-correlates`

## Goal
Predict FWI at 5 PEINP park stations using ECCC Stanhope weather as the anchor,
translated via OLS regression and computed through the standard FWI equations.

## Pipeline Architecture
```
OWM One Call 3.0 (Stanhope coords, 1 API call)
  → OLS translate (per variable, per park station)
    → FWI computation (FFMC → DMC → DC → ISI → BUI → FWI)
      → 48-hour FWI forecast per park station
```

## Design Decisions

### Single fetch point (Stanhope)
- Stanhope is our ECCC reference — all OLS relationships built around it
- 1 API call per run vs 6 (stays well under 1,000/day free tier)
- Regression translates regional conditions → each park's microclimate
- Validate by comparing OWM per-station spatial resolution against OLS translation

### OLS regression (not ML)
- ~26K hours of paired Stanhope ↔ park station data in DB
- Fit per variable per station: `park_var = slope × stanhope_var + intercept`
- Variables: air_temperature_c, relative_humidity_pct, wind_speed_kmh, rain_mm
- Coefficients stored as JSON artifact — transparent, auditable, regenerable

### FWI computation
- Reuse existing `src/pea_met_network/fwi.py`
- Inputs: temp (°C), RH (%), wind (km/h), rain (mm)
- Outputs: FFMC, DMC, DC, ISI, BUI, FWI

### API key protection
- Read from `os.environ["openweather_key"]` — hard fail if missing
- Key is in Moltis vault, not in repo
- `.env` already in `.gitignore`

## Outputs
- DataFrame: station × hour × FWI components
- Daily max FWI summary per station
- CLI entry point: `python -m pea_met_network.fwi_forecast`

## Implementation Steps

### Step 1: Fit OLS coefficients from historical data
- Query paired hourly data (Stanhope ↔ each park station)
- Fit `ols_results.json` with slope, intercept, R², std_error per variable per station
- Save to `data/processed/ols_coefficients.json`

### Step 2: Build fetch + translate + FWI pipeline
- `src/pea_met_network/fwi_forecast.py` — main module
  - `fetch_forecast()` — OWM One Call 3.0 fetch (Stanhope coords)
  - `translate_to_station()` — OLS translation per park station
  - `compute_fwi_series()` — wrap existing fwi.py for hourly series
  - `run_forecast()` — end-to-end pipeline
- CLI entry point in `pyproject.toml`

### Step 3: Validate OLS translation against actual records
- Holdout test: train on 80% of historical data, test on 20%
- Report RMSE per variable per station
- Compare OLS translation vs direct OWM per-station fetch

### Step 4: Compare OWM per-station vs OLS translation
- Fetch OWM for all 6 station coords
- Compute FWI both ways (direct OWM vs OLS-translated)
- Quantify divergence — informs whether single-point fetch is sufficient
