# Project Contract

## Project
DATA-3210 Semester Project: Meteorological Network Optimization & Predictive Modeling

Client: Parks Canada Agency (PEI Field Unit)

## Delivery Bias
Build for both:
- assignment compliance first
- production-ish internal structure second

Do not over-engineer beyond what improves clarity, reproducibility,
and maintainability.

## Assignment Deliverables
The repository must contain at minimum:
- `README.md` with setup and execution instructions
- `cleaning.py` as the assignment-facing pipeline entrypoint
- `analysis.ipynb` with documented EDA, redundancy analysis,
  FWI logic, and probabilistic visualizations

Supporting structure may include:
- `src/pea_met_network/` for reusable logic
- `tests/` for validation
- `docs/` for working notes and diary logs
- `data/` for raw, processed, and external reference data

## Core Outcomes
The project must produce evidence-based answers to:
1. Are any PCA stations redundant?
2. How similar are PCA stations to the ECCC Stanhope reference?
3. Can daily FWI values, especially moisture codes, be calculated
   reliably for Cavendish and Greenwich?
4. What is the uncertainty of removing a station?

## OSEMN Framing
Use OSEMN as the narrative and execution structure:
- Obtain
- Scrub
- Explore
- Model
- Interpret

This is a planning lens, not a software framework.

## Stable Constraints
- Python-first pipeline, not notebook-first
- Real logic belongs in `src/` or entry scripts
- Notebook is for narrative, visuals, and documented analysis
- Cached local data is canonical once acquired
- External fetches should be minimized and cached
- Commits must represent passing, coherent units of work

## Done Definition
The project is done when all of the following are true:
- raw station data ingests reproducibly
- timestamps are normalized consistently
- hourly and daily datasets are produced reproducibly
- imputation is conservative, transparent, and auditable
- Stanhope reference data is scripted and cached locally
- FWI moisture codes are computed for Cavendish and Greenwich
- full FWI chain is attempted if data supports it
- redundancy analysis includes PCA and clustering
- uncertainty analysis estimates risk of station removal
- README supports fresh setup and execution
- assignment-facing files exist and are usable
