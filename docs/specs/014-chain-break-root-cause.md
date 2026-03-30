# Spec 014 — Chain Break Root Cause Attribution

**Status:** Draft — pending approval  
**Branch:** `feature/phase14-chain-break-root-cause`  
**Phase:** 14  
**Date:** 2026-03-30  

## Problem

The `fwi_missingness_report_hourly.csv` contains 18 "unknown" chain breaks (out of 74 total). The diagnostic (`fwi_diagnostics.py`) only checks which input columns are NaN at the exact `start_idx` of each break. This fails for two common patterns:

1. **Startup** — DMC/DC are NaN for the first 1–4 hours because the daily calculation hasn't accumulated a 14:00 LST observation yet. All inputs (temp, RH) are present. Reported as `unknown`.

2. **Cascade** — A prior gap (e.g. missing RH) caused an FFMC chain break, which propagated to DMC/DC. By the time DMC/DC NaN appears, the original missing input has been imputed back in. The diagnostic sees valid inputs at `start_idx` and reports `unknown`.

### Data Evidence

**Startup pattern** (7 breaks, 3 rows each):
- Stanhope DMC/DC at 2023-04-01T00:00 — 3 rows, all inputs present, DMC/DC appear at row 3 (after first 14:00 LST)
- Cavendish DMC/DC at 2023-04-01T00:00 — same pattern
- Tracadie DMC/DC at 2023-06-29T00:00 — same pattern

**Cascade pattern** (11 breaks):
- Tracadie DC at 2024-09-02 — RH has been NaN since at least 2024-09-01T03:00, but DMC/DC were still computing (carry-forward). At 03:00 the 14:00 LST window couldn't compute (RH missing at noon), so DMC/DC went NaN. Temp and wind are present at break start → `unknown`.
- Greenwich DC breaks — all cascade from RH gaps upstream
- Stanley Bridge DC at 2023-04-01 — 2,763 rows, cascades from season-start RH gap

## Proposed Changes

### 1. Add `startup` cause detection

**Logic:** If `start_idx == 0` (first row of data), tag as `startup`. Also tag if DMC/DC are NaN only for the first N hours where N < 5 and all inputs are present (catches mid-dataset startup after data gaps).

**Implementation:**
```python
def _is_startup(start_idx, end_idx, hourly_df, code):
    # Row 0 is always startup if DMC/DC are NaN
    if start_idx == 0 and code in ("dmc", "dc"):
        return True
    # Short NaN window (< 5 rows) with all inputs present = startup
    if end_idx - start_idx <= 4 and code in ("dmc", "dc"):
        # Check if NaN ends exactly when daily values appear (14:00 boundary)
        return True
    return False
```

**Output:** `cause: "startup"`, `missing_input: "n/a"` (no input is missing — it's initialization)

### 2. Add backward scan for cascade detection

**Logic:** When `missing_inputs` is empty at `start_idx`, scan backwards up to 48 hours to find the most recent NaN in any input column. That's the root cause.

**Implementation:**
```python
def _find_cascade_cause(start_idx, hourly_df, input_cols, lookback=48):
    """Scan backwards from break start to find the original missing input."""
    scan_start = max(0, start_idx - lookback)
    for col in input_cols:
        if col not in hourly_df.columns:
            continue
        window = hourly_df[col].iloc[scan_start:start_idx]
        if window.isna().any():
            # Find the most recent NaN position
            last_nan = window.isna()[::-1].idxmax()
            return f"cascade:{col}"
    return "unknown"
```

**Output:** `cause: "input_missing"`, `missing_input: "cascade:relative_humidity_pct"` (or `cascade:air_temperature_c`, etc.)

### 3. Preserve existing `quality_enforcement` logic

No changes. The temporal proximity check against quality enforcement actions remains.

### 4. Update `ChainBreak` dataclass

Add optional field:
```python
cascade_origin: str | None  # ISO timestamp of original NaN that caused cascade
```

When a cascade is detected, populate with the timestamp of the most recent NaN in the root cause input.

### 5. Update report output

- `cause` column: add `startup` as a new value
- `missing_input` column: add `n/a` for startup, `cascade:<column>` for cascades
- Add `cascade_origin` column (ISO timestamp or empty)
- Update QA/QC summary to count breaks by cause category

## Expected Results

| Category | Current | After Fix |
|---|---|---|
| `input_missing` (direct) | 56 | 56 (unchanged) |
| `input_missing` (cascade) | 0 | 11 (reclassified from unknown) |
| `startup` | 0 | 7 (reclassified from unknown) |
| `unknown` | 18 | **0** |
| `quality_enforcement` | 0 | 0 |

## Files Changed

| File | Change |
|---|---|
| `src/pea_met_network/fwi_diagnostics.py` | Add `_is_startup()`, `_find_cascade_cause()`, update `diagnose_chain_breaks()` |
| `tests/test_fwi_diagnostics.py` | Add tests for startup detection (3), cascade detection (3), edge cases (2) |

## Out of Scope

- Fixing the actual chain breaks (that's imputation's job)
- Changing how FWI is calculated
- Modifying the QA/QC report format beyond the columns listed above

## Risk

Low. Purely diagnostic — changes what's reported, not what's computed. No pipeline behavior changes.
