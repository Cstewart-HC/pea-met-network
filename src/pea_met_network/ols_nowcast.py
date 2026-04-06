"""OLS Nowcast — predict park station weather from Stanhope ECCC observations.

Uses bulk CSV endpoint (climate.weather.gc.ca) to fetch recent Stanhope hourly
observations, then applies per-station OLS coefficients to predict weather at
each of the 5 PEINP park stations.

This provides 0-3h nowcast-quality data for the FWI pipeline, bridging the gap
between real-time ECCC obs and OWM model forecasts.

Design decisions:
  - Uses the old bulk CSV endpoint (stationID=6545), not the OGC API.
    The OGC API's climate-hourly collection for Stanhope (CLIMATE_ID=8300590)
    is stale (stops at 2023-05-08). The bulk endpoint is current.
  - Fetches current month's CSV; filters to last N hours client-side.
  - Rain is not translated via OLS (R² < 0.1 for all stations — rain is
    spatially discontinuous and OLS can't model it). Falls back to 0.0 mm
    for the nowcast window, which is conservative (assumes no rain) and
    acceptable for a 1-3h window.
  - Temperature, RH, wind are translated with decent R² (0.14–0.93).

Usage:
    from pea_met_network.ols_nowcast import fetch_stanhope_recent, apply_ols_nowcast
    stanhope_obs = fetch_stanhope_recent(hours=6)
    park_weather = apply_ols_nowcast(stanhope_obs, hours=3)
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import urlopen

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STANHOPE_WEATHERCAN_ID = 6545
BULK_CSV_URL = (
    "https://climate.weather.gc.ca/climate_data/bulk_data_e.html?"
    "format=csv&stationID={station_id}&Year={year}&Month={month}"
    "&Day=1&timeframe=1&submit=Download+Data"
)

# Variables we translate via OLS
TRANSLATED_VARS = ["air_temperature_c", "relative_humidity_pct", "wind_speed_kmh"]

# Rain is not translated (R² < 0.1 everywhere) — too spatially discontinuous.
# For a 1-3h nowcast window, assuming 0.0 is conservative and acceptable.
NO_RAIN_MM = 0.0

# Required columns in the weather DataFrame for FWI computation
WEATHER_COLS = ["air_temperature_c", "relative_humidity_pct", "wind_speed_kmh", "rain_mm"]

# OLS coefficients path (relative to project root)
COEFFICIENTS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "ols_coefficients.json"


# ---------------------------------------------------------------------------
# Stanhope observation fetch
# ---------------------------------------------------------------------------

def _fetch_bulk_month(year: int, month: int) -> pd.DataFrame:
    """Fetch one month of Stanhope hourly data from the bulk CSV endpoint."""
    url = BULK_CSV_URL.format(station_id=STANHOPE_WEATHERCAN_ID, year=year, month=month)

    logger.info("Fetching Stanhope bulk CSV (station %d, %d-%02d)", STANHOPE_WEATHERCAN_ID, year, month)

    try:
        with urlopen(url, timeout=60) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8-sig")
    except HTTPError as e:
        if e.code == 404 or e.code == 400:
            # Month not yet available (data lag at start of month)
            logger.debug("No bulk CSV for %d-%02d (HTTP %d)", year, month, e.code)
            return pd.DataFrame()
        raise RuntimeError(
            f"Failed to fetch Stanhope bulk CSV: HTTP {e.code}"
        ) from e

    df = pd.read_csv(StringIO(raw))
    return _normalize_stanhope_bulk(df)


def fetch_stanhope_recent(
    hours: int = 6,
    *,
    now: datetime | None = None,
) -> pd.DataFrame:
    """Fetch recent Stanhope hourly observations from the bulk CSV endpoint.

    Fetches the current month's CSV (falling back to previous month if current
    month has no data yet — ECCC typically has a 1-2 day lag at month start).
    Filters to the last ``hours`` rows with complete weather data.

    Args:
        hours: How many hours of history to return (default 6).
        now: Override current time (for testing). Defaults to UTC now.

    Returns:
        DataFrame with index ``timestamp_utc`` and columns matching WEATHER_COLS.
        May return fewer than ``hours`` rows if data is sparse.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    year, month = now.year, now.month

    # Try current month first, fall back to previous month
    df = _fetch_bulk_month(year, month)
    if df.empty and month == 1:
        df = _fetch_bulk_month(year - 1, 12)
    elif df.empty:
        df = _fetch_bulk_month(year, month - 1)

    if df.empty:
        logger.warning("No Stanhope data available for %d-%02d or previous month", year, month)
        return df

    # Filter to complete rows and recent hours
    cutoff = now - timedelta(hours=hours)
    complete = df.dropna(subset=TRANSLATED_VARS)
    recent = complete[complete.index >= cutoff].sort_index()

    logger.info(
        "Stanhope: %d total rows, %d complete, %d in last %dh",
        len(df), len(complete), len(recent), hours,
    )
    return recent


def _normalize_stanhope_bulk(df: pd.DataFrame) -> pd.DataFrame:
    """Convert bulk CSV columns to our weather schema."""
    # Column mapping (same as stanhope_cache.py)
    rename = {
        "Temp (°C)": "air_temperature_c",
        "Rel Hum (%)": "relative_humidity_pct",
        "Wind Spd (km/h)": "wind_speed_kmh",
        "Precip. Amount (mm)": "rain_mm",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    # Parse timestamps
    ts_col = "Date/Time (LST)"
    if ts_col in df.columns:
        timestamps = pd.to_datetime(df[ts_col].astype(str).str.strip(), format="%Y-%m-%d %H:%M")
        timestamps = timestamps.dt.tz_localize(
            "America/Halifax", nonexistent="shift_forward", ambiguous="infer"
        ).dt.tz_convert("UTC")
    else:
        raise ValueError(f"Expected column '{ts_col}' not found in bulk CSV")

    # Build result
    result = pd.DataFrame({"timestamp_utc": timestamps})
    for col in WEATHER_COLS:
        if col in df.columns:
            result[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            result[col] = pd.NA

    result = result.set_index("timestamp_utc").sort_index()
    return result


# ---------------------------------------------------------------------------
# OLS translation
# ---------------------------------------------------------------------------

def load_coefficients(path: Path = COEFFICIENTS_PATH) -> dict[str, dict[str, dict[str, float]]]:
    """Load OLS coefficients from JSON.

    Returns:
        {station_name: {variable_name: {slope, intercept, r_squared, ...}}}
    """
    if not path.exists():
        raise FileNotFoundError(
            f"OLS coefficients not found at {path}. "
            "Run scripts/fit_ols_coefficients.py first."
        )
    import json
    return json.loads(path.read_text())


def apply_ols_nowcast(
    stanhope_obs: pd.DataFrame,
    *,
    hours: int = 3,
    coefficients: dict[str, dict[str, dict[str, float]]] | None = None,
) -> dict[str, pd.DataFrame]:
    """Apply OLS coefficients to translate Stanhope obs → predicted park weather.

    Args:
        stanhope_obs: DataFrame from ``fetch_stanhope_recent()`` with index
            ``timestamp_utc`` and weather columns.
        hours: Number of recent hours to include in the nowcast (default 3).
        coefficients: Pre-loaded OLS coefficients. Loaded from disk if None.

    Returns:
        Dict mapping park station name → DataFrame with WEATHER_COLS,
        ready to feed into ``compute_fwi_series()``.
    """
    if coefficients is None:
        coefficients = load_coefficients()

    # Take only the last N hours
    recent = stanhope_obs.tail(hours)

    results: dict[str, pd.DataFrame] = {}

    for station_name, var_coeffs in coefficients.items():
        rows = []
        for ts, row in recent.iterrows():
            translated: dict[str, Any] = {"timestamp_utc": ts}

            for var in TRANSLATED_VARS:
                if var not in var_coeffs:
                    logger.warning("No OLS coefficients for %s/%s, skipping", station_name, var)
                    continue

                coeffs = var_coeffs[var]
                sth_val = row.get(var)

                if pd.isna(sth_val):
                    translated[var] = pd.NA
                else:
                    translated[var] = coeffs["slope"] * sth_val + coeffs["intercept"]

            # Rain: not translated (R² < 0.1), use Stanhope's observed rain directly
            # as a reasonable proxy for 1-3h ahead in the same weather system.
            # This is better than assuming 0.0 for rain events.
            translated["rain_mm"] = row.get("rain_mm", NO_RAIN_MM)

            # Clamp values to physically plausible ranges
            translated["air_temperature_c"] = max(-50.0, min(60.0, translated.get("air_temperature_c", 0.0)))
            translated["relative_humidity_pct"] = max(0.0, min(100.0, translated.get("relative_humidity_pct", 50.0)))
            translated["wind_speed_kmh"] = max(0.0, min(200.0, translated.get("wind_speed_kmh", 0.0)))
            translated["rain_mm"] = max(0.0, translated.get("rain_mm", 0.0))

            rows.append(translated)

        if rows:
            df = pd.DataFrame(rows)
            df = df.set_index("timestamp_utc").sort_index()
            results[station_name] = df
            logger.info(
                "%s nowcast: %d hours (%s → %s)",
                station_name, len(df),
                df.index[0].strftime("%H:%MZ"),
                df.index[-1].strftime("%H:%MZ"),
            )

    return results
