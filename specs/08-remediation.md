# Remediation Spec — Phases 1-4 Retroactive Review

## Goal
Address gaps in Phases 1-4 that were completed before adversarial review
was introduced. These phases were marked "done" without UnRalph
verification.

## Scope
This phase targets specific, measurable deficiencies discovered during
a manual audit of Phases 1-4 against their original specs.

## Remediation Items

### REM-1: FWI tests must validate outputs, not just vector shapes

**Current state:** `tests/test_fwi_vectors.py` defines reference vectors
(FFMC, DMC, DC) but the test functions only assert that input fields
exist and expected values are non-negative. No test calls the actual
implementation and compares against the expected output.

**Required:** Each vector test must call the corresponding moisture-code
function (`fine_fuel_moisture_code`, `duff_moisture_code`,
`drought_code`) and assert the result matches `expected` within a
tolerance (e.g. `abs(result - expected) < 0.01`).

**Spec reference:** `04-fwi.md` — "validation artifacts compare outputs
to external references" and "validation must include reproducible
checks, not just visual inspection."

### REM-2: DMC and DC must be implemented

**Current state:** `src/pea_met_network/fwi.py` only contains
`fine_fuel_moisture_code`. DMC and DC vectors exist in tests but have
no implementation.

**Required:** Implement `duff_moisture_code` and `drought_code` in
`src/pea_met_network/fwi.py` following the Canadian FWI system
formulas. Use `gagreene/cffdrs` as the reference implementation for
correctness.

**Spec reference:** `04-fwi.md` — milestone order item 2: "Compute
moisture codes: FFMC, DMC, DC."

### REM-3: Imputation framework must exist

**Current state:** `02-data-pipeline.md` requires conservative,
auditable imputation with per-station, per-variable, per-time-range
reporting. No imputation code exists anywhere in the project.

**Required:** Create `src/pea_met_network/imputation.py` with:
- a configurable imputation strategy (short-gap: bounded interpolation;
  long-gap: preserve missingness)
- an audit trail function that returns: station, variable, time range,
  method, count of values affected
- integration with the existing pipeline (`resampling.py` /
  `materialize_resampled.py`)

**Spec reference:** `02-data-pipeline.md` — "Imputation Policy" and
"Imputation Audit Requirements" sections.

### REM-4: QA/QC summary artifacts must exist

**Current state:** `02-data-pipeline.md` requires missingness summaries,
duplicate detection, impossible values, timezone anomalies, and
coverage reports. None of these exist as automated outputs.

**Required:** Create `src/pea_met_network/qa_qc.py` with functions that
produce:
- missingness by station and variable
- duplicate timestamp detection
- out-of-range value detection
- coverage summary by station and date range

Output format: a DataFrame or dict that can be inspected or written to
file. Must be testable with synthetic data.

**Spec reference:** `02-data-pipeline.md` — "QA/QC Requirements"
section.

### REM-5: Loader must handle multiple schema families

**Current state:** `normalized_loader.py` hardcodes a single timestamp
format (`%m/%d/%Y %H:%M:%S %z`). The manifest recognizes 4 schema
families but the loader only handles the Date+Time format. Other
families would fail silently.

**Required:** `load_normalized_station_csv` must detect the schema
family (using `recognize_schema`) and apply the appropriate timestamp
parsing strategy for each family. If a schema family is recognized but
not yet supported, raise a clear `NotImplementedError` rather than
failing silently.

**Spec reference:** `02-data-pipeline.md` — "Parse station-specific
schemas" and "Explicitly track timezone assumptions and conversions."

### REM-6: Explore phase must have automated verification

**Current state:** Phase 3 exit criteria ("notebook runs on cleaned
data, exploratory summaries exist") has no automated test. If the
notebook broke, nobody would know.

**Required:** Add a smoke test that verifies:
- the notebook file exists
- it can be executed programmatically (e.g. via `nbconvert` or
  `jupyter execute`) without errors on the cleaned test data
- or, if full notebook execution is too expensive, verify that all
  required input files are present and the notebook imports succeed

**Spec reference:** Phase 3 exit criteria in `ralph-state.json`.

## Acceptance Criteria

This spec is satisfied when all of the following are true:

- **AC-REM-1:** `test_fwi_vectors.py` calls moisture-code functions and
  asserts output matches reference vectors within tolerance
- **AC-REM-2:** `fwi.py` contains working `duff_moisture_code` and
  `drought_code` implementations that pass their reference vectors
- **AC-REM-3:** `imputation.py` exists with configurable strategy and
  audit trail; tests verify audit output format
- **AC-REM-4:** `qa_qc.py` exists with missingness, duplicate, and
  out-of-range functions; tests verify output with synthetic data
- **AC-REM-5:** `normalized_loader.py` handles multiple schema families
  or raises clear errors for unsupported ones; tests cover at least 2
  families
- **AC-REM-6:** An automated test verifies the explore notebook is
  executable or at least importable without errors

## Exit Command

```bash
.venv/bin/pytest tests/test_fwi_vectors.py tests/test_imputation.py tests/test_qa_qc.py tests/test_normalized_loader.py tests/test_explore_smoke.py -q
```

## Notes

- This phase runs after Phase 6 (Interpret) completes
- Each remediation item is independent and can be addressed in any
  order
- REJECT-repair batching is appropriate here since items are isolated
- The orchestrator should treat this as a normal phase with the above
  exit command
