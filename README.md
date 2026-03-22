# pea-met-network

This repository is an experiment in AI-assisted analytics development.
It applies a visible Ralph-style loop to a DATA-3210 semester project for
Parks Canada Agency (PEI Field Unit).

The goal is to determine weather-station redundancy across Prince Edward
Island National Park and automate Canadian Fire Weather Index (FWI)
calculation for localized wildfire risk management.

## Project status
The project is past initial planning and data audit work and has entered
real ingestion implementation.

Implemented so far:
- planning stack and working agreement
- repository quality rails and shape enforcement
- raw data inventory and schema audit
- raw manifest loader and schema recognition
- timestamp normalization across observed schema families
- deterministic local virtual environment workflow

See `docs/status.md` for the current checkpoint summary.

## Assignment context
**DATA-3210: Advanced Concepts in Data — Semester Project**

Client: Parks Canada Agency (PEI Field Unit)

Required themes:
- Python-based data pipeline and QA/QC
- station redundancy analysis using PCA and/or clustering
- FWI calculation and validation
- probabilistic uncertainty quantification

## Repository structure

```text
pea-met-network/
├── data/
│   ├── raw/
│   ├── processed/
│   └── external/
├── docs/
├── notebooks/
├── specs/
├── src/
├── tests/
├── IMPLEMENTATION_PLAN.md
├── Makefile
├── README.md
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Or use:

```bash
make install
```

## Quality checks

```bash
make lint
make test
make check
```

## Current implementation path
1. Obtain: inventory and schema grounding
2. Scrub: ingestion, normalization, resampling, imputation
3. Explore: notebook and QA/QC summaries
4. Model: Stanhope reference, FWI, redundancy analysis
5. Interpret: uncertainty and recommendation outputs

## Notes on autonomy
This repository is being developed with observation by default.
Manual and scheduled loops should leave visible artifacts:
- diary entries
- progress markers or standup summaries
- verifiable commits

No black-box runs.
