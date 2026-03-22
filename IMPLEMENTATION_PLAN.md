# Implementation Plan — PEI Meteorological Network Optimization

## Project: DATA-3210 Semester Project
## Client: Parks Canada Agency (PEI Field Unit)
## Last Updated: 2026-03-21

---

## Status: PRE-LAUNCH

## Completed
- [x] Project scaffolding
- [x] Git initialization
- [x] Research (Ralph loop methodology, ECCC API, FWI libraries)

## In Progress
- [ ] Spec generation (awaiting data + go signal from MrCoins)

## TODO (ordered by dependency)
1. Receive student data files (CSVs + Excel)
2. Receive GitHub remote credentials
3. Spec generation phase (decompose assignment into implementation topics)
4. Write PROMPT.md (top-level loop prompt)
5. Write AGENTS.md (how to build, test, verify)
6. Write per-topic spec files in specs/
7. Scaffold data pipeline (cleaning.py)
8. Scaffold FWI module (src/fwi.py)
9. Scaffold analysis notebook (analysis.ipynb)
10. Write initial tests (tests/)
11. Launch Ralph loop

---

## Architecture Decisions
- Language: Python 3.11
- FWI: cffdrs library (pip install cffdrs)
- ECCC data: Bulk CSV download with rate limiting
- Imputation: TBD (will research during spec phase)
- Redundancy analysis: PCA + K-Means clustering
- Uncertainty: KDE via scipy

## Key Files
- `IMPLEMENTATION_PLAN.md` — this file (loaded every loop iteration)
- `PROMPT.md` — top-level prompt for the Ralph loop
- `AGENTS.md` — build/test/verify instructions
- `cleaning.py` — data pipeline
- `analysis.ipynb` — EDA + analysis
- `src/fwi.py` — FWI calculation module
- `src/redundancy.py` — PCA/clustering analysis
- `src/uncertainty.py` — KDE uncertainty quantification

## Stations
| Station | Source | Notes |
|---|---|---|
| Cavendish | PCA (internal CSVs) | Primary FWI target |
| Stanley Bridge | PCA (internal CSVs) | |
| Tracadie | PCA (internal CSVs) | |
| Greenwich | PCA (internal CSVs) | Primary FWI target |
| North Rustico | PCA (internal CSVs) | |
| Stanhope | ECCC (ID: 8300590) | Reference station, external API |

