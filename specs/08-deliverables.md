# Phase 8: Deliverables

## Scope
Produce the assignment-facing deliverables required by `specs/01-project-contract.md`.

## Acceptance Criteria

### AC-DLV-1: README with setup and execution instructions
`README.md` must include:
- project description and client context (Parks Canada, PEI Field Unit)
- Python version and dependency installation (`pip install -r requirements.txt`)
- how to run `cleaning.py` end-to-end
- how to open and run `analysis.ipynb`
- brief description of the OSEMN pipeline structure
- list of key outputs (cleaned datasets, FWI values, redundancy/uncertainty results)
- the README must reflect the **actual** current state of the project, not a stale snapshot

### AC-DLV-2: cleaning.py pipeline entrypoint
`cleaning.py` must exist at the repository root and:
- be importable and executable (`python cleaning.py`)
- produce cleaned hourly and daily datasets for all PCA stations
- output to a configurable location (default: `data/processed/`)
- log what it does (stations loaded, rows after cleaning, imputation applied)
- not require any manual steps between start and finished output
- handle missing data directories gracefully with a clear error message

### AC-DLV-3: analysis.ipynb with documented narrative
`analysis.ipynb` must exist at the repository root and:
- run top-to-bottom without errors on cleaned data
- contain sections for EDA, redundancy analysis, FWI logic, and uncertainty
- include at least one visualization per section (EDA plots, PCA biplot/clustering, FWI time series, uncertainty distributions)
- have markdown cells explaining the narrative — what was found, why it matters
- reference the OSEMN framing
- not contain dead-code cells or placeholder sections

### AC-DLV-4: Full FWI chain attempted
The analysis must show evidence that the full FWI chain (FFMC → DMC → DC → ISI → BUI → FWI) was attempted, not just moisture codes. If data limitations prevent full chain completion, this must be documented with specifics.

### AC-DLV-5: Smoke test for deliverables
`tests/test_deliverables.py` must verify:
- `cleaning.py` is importable and `cleaning.main()` exists
- `analysis.ipynb` exists and is valid JSON (well-formed notebook)
- `README.md` exists and contains "Parks Canada" and "installation" (or "install")
