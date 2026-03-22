# Data Pipeline Spec

## Goal
Build a reproducible Python pipeline to ingest, clean, standardize,
and resample the PEINP weather station telemetry data.

## Inputs
- Raw CSVs from PCA stations, 2022-2025
- A small number of Excel-family files
- ECCC Stanhope reference data and metadata

## Required Outputs
At minimum produce:
- standardized raw inventory manifest
- cleaned hourly dataset(s)
- cleaned daily dataset(s)
- QA/QC summary artifacts
- imputation audit artifacts

## Pipeline Responsibilities
1. Discover and inventory raw files
2. Parse station-specific schemas
3. Standardize column names and units where possible
4. Normalize timestamps to UTC
5. Resample minute-level or irregular data to hourly and daily
6. Handle missing values via a conservative strategy
7. Record QA/QC and imputation metadata

## Timestamp Rules
- Preserve original timestamp fields where useful
- Produce a canonical UTC timestamp field
- Explicitly track timezone assumptions and conversions
- Avoid silent timezone coercion
- Any ambiguous timestamps must be surfaced in QA output

## Resampling Rules
- Hourly and daily aggregation logic must be explicit by variable
- Avoid mixing incompatible aggregation methods
- Aggregation assumptions must be documented
- Derived daily values must be reproducible from cleaned hourly data
  where appropriate

## Imputation Policy
Use conservative, transparent, auditable imputation.

### Short gaps
Allow bounded interpolation or limited forward/back fill where
scientifically reasonable.

### Medium gaps
Allow cautious station-history or hour-of-day based estimates only if
well justified and clearly flagged.

### Long gaps
Prefer preserving missingness over inventing certainty.

## Imputation Audit Requirements
Every imputation workflow must support reporting:
- station
- variable
- time range
- method used
- count of values affected

Do not silently overwrite missing values without traceability.

## QA/QC Requirements
Surface at minimum:
- missingness by station and variable
- duplicate timestamps
- impossible or suspicious values
- out-of-range observations
- timezone/parsing anomalies
- coverage by station and date range

## Acceptance Criteria
This spec is satisfied when:
- a fresh run produces deterministic cleaned outputs
- hourly and daily products are generated reproducibly
- missingness and imputation are auditable
- QA/QC summaries exist and reflect actual data issues
