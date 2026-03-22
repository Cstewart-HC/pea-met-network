# pea-met-network

This repository is an experiment in analytics. It is controlled almost autonomously by an AI agent on a loop using moltis. The goal is to see if the agent looping over and over ala the Ralph Wiggum Technique can complete a data analytics project to a satisfactoy degree.

**DATA-3210: Advanced Concepts in Data — Semester Project**

Client: Parks Canada Agency (PEI Field Unit)

## Overview

Parks Canada operates five autonomous weather stations across Prince Edward Island National Park. This project determines station redundancy and automates Fire Weather Index (FWI) calculation for wildfire risk management.

## Project Structure

```
pea-met-network/
├── data/
│   ├── raw/           # Ingested raw CSVs
│   ├── processed/     # Cleaned, standardized datasets
│   └── external/      # ECCC Stanhope reference data
├── src/
│   ├── fwi.py         # FWI calculation module
│   ├── redundancy.py  # PCA/clustering analysis
│   └── uncertainty.py # KDE uncertainty quantification
├── notebooks/
│   └── analysis.ipynb # EDA + visualizations
├── tests/
├── docs/
├── specs/
├── cleaning.py        # Data pipeline entry point
├── IMPLEMENTATION_PLAN.md
├── PROMPT.md
└── AGENTS.md
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Pipeline

```bash
python cleaning.py                    # Ingest & clean data
python -m src.fwi                     # Calculate FWI
jupyter notebook notebooks/analysis.ipynb  # EDA & visualization
pytest tests/                         # Run test suite
```

## Stations

| Station | Source | Role |
|---|---|---|
| Cavendish | PCA | Primary FWI target |
| Stanley Bridge | PCA | Redundancy analysis |
| Tracadie | PCA | Redundancy analysis |
| Greenwich | PCA | Primary FWI target |
| North Rustico | PCA | Redundancy analysis |
| Stanhope (8300590) | ECCC | Reference station |

---

*Automated development via Ralph Loop methodology.*
