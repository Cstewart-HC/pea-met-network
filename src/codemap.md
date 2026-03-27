# src/

## Responsibility
Source root containing the `pea_met_network` Python package. No code lives directly in this directory.

## Structure
- `pea_met_network/` — The main (and only) package. All library code lives here.
  - `adapters/` — Format adapter layer (Strategy pattern) for CSV, XLSX, XLE, JSON
  - `cleaning.py` — Full pipeline orchestrator (entry point)
  - `validation.py` — Stanhope cross-validation utilities
  - `__main__.py` — CLI entry point (`python -m pea_met_network`)

## Dependencies
- Consumed by: `tests/`
- Depends on: `pyproject.toml` for build metadata and dependencies
- CLI entry: `python -m pea_met_network --stations all [--force] [--dry-run]`
