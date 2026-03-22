# Fire Weather Index Spec

## Goal
Implement a Python module that calculates daily Fire Weather Index values,
with moisture codes as the first milestone and the full chain as the
stretch target when data supports it.

## Primary Stations
- Cavendish
- Greenwich

## Milestone Order
1. Validate required meteorological inputs
2. Compute moisture codes:
   - FFMC
   - DMC
   - DC
3. Extend to full chain if feasible:
   - ISI
   - BUI
   - FWI
   - DSR if supported

## Validation Strategy
- Cross-reference results against published ECCC FWI values where
  available
- Document input assumptions
- Record any unavoidable deviations or data limitations

## Implementation Rules
- Core logic must live in Python modules, not only in notebook cells
- If a library is used, wrap it in project code with explicit interfaces
- Validation must include reproducible checks, not just visual inspection

## Input Requirements
The implementation must make input assumptions explicit, including:
- required variables
- units and conversions
- daily aggregation assumptions
- handling of missing values
- station-specific coverage limitations

## Acceptance Criteria
This spec is satisfied when:
- daily moisture codes are reproducibly computed for Cavendish and
  Greenwich where data supports it
- validation artifacts compare outputs to external references
- the path to full-chain FWI is implemented or explicitly justified if
  blocked by data limitations

## Implementation Decision (2026-03-22)

- `cffdrs` is an **R package**, not a Python package, and must not be listed as a Python dependency.
- The project will implement the Canadian FWI logic **natively in Python** under `src/pea_met_network/`.
- The GitHub repository `gagreene/cffdrs` is an acceptable **MIT-licensed Python reference implementation** and test-source candidate.
- The GitHub repository `cffdrs/cffdrs_r` is an acceptable **authoritative R reference/oracle**, but because it is GPL-2, it should be treated as a behavioral reference rather than a copy source.
- Validation priority:
  1. published ECCC outputs
  2. parity spot-checks against `gagreene/cffdrs`
  3. formula/behavior checks against `cffdrs_r`

## Runtime Policy

- No FWI runtime dependency is to be added unless a real, maintained Python package with a suitable license is verified.
- Prefer small, typed functions over vendoring a foreign codebase wholesale.
- Moisture codes (FFMC, DMC, DC) remain the first milestone; full-chain FWI remains the target.
