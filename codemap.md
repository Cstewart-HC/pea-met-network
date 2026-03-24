# Repository Atlas: pea-met-network

## Project Responsibility
Autonomous weather station data pipeline with adversarial quality control for the PEI meteorological network. Computes Fire Weather Index (FWI) system metrics, performs redundancy analysis, and estimates uncertainty for station removal recommendations.

## System Entry Points
- `cleaning.py`: Assignment-facing pipeline entrypoint — iterates stations, normalizes, resamples, and materializes outputs.
- `src/pea_met_network/__init__.py`: Package initialization.
- `scripts/sync_state.py`: State machine operator — manages phase transitions, verdict validation, circuit breaker, and auto-commit.
- `scripts/record_verdict.py`: Deterministic verdict recording — captures HEAD, updates `validation.json`, commits.

## Directory Map

| Directory | Responsibility | Detailed Map |
|-----------|----------------|--------------|
| `src/pea_met_network/` | Core library — ingestion, normalization, resampling, FWI, imputation, QA/QC, redundancy, uncertainty | [codemap.md](src/pea_met_network/codemap.md) |
| `src/` | Source root — contains the `pea_met_network` package | [codemap.md](src/codemap.md) |
| `scripts/` | Infrastructure — state machine, verdict recording, pipeline utilities | N/A (not mapped) |
| `tests/` | Test suite — acceptance criteria verification per phase | N/A (excluded from maps) |
| `specs/` | Human-reviewed specifications and acceptance criteria | N/A (excluded from maps) |
| `docs/` | Loop prompts, state files, validation, diary | N/A (excluded from maps) |
| `notebooks/` | Analysis notebook (EDA, FWI, redundancy, uncertainty) | N/A (excluded from maps) |

## Data Flow
```
data/raw/peinp/*.csv
    → manifest.py (file discovery, station inference)
    → normalized_loader.py (schema recognition, column rename, timestamp parsing)
    → imputation.py (gap filling with audit trail)
    → qa_qc.py (missingness, duplicates, out-of-range detection)
    → resampling.py (hourly/daily aggregation)
    → fwi.py (FFMC → DMC → DC → ISI → BUI → FWI)
    → stanhope_cache.py (reference station data from ECCC)
    → redundancy.py (PCA, clustering, benchmarking, recommendations)
    → uncertainty.py (KDE-based risk estimation)
    → data/processed/*.csv (materialized outputs)
    → notebooks/analysis.ipynb (narrative and visualizations)
```

## Key Design Decisions
- **Single monolithic package** — no multi-agent complexity, one repo, one loop.
- **State machine** in `ralph-state.json` — phases 1-11, each with exit gates.
- **Adversarial review** via Lisa — never self-approve.
- **Deterministic state management** — scripts mutate state, prompts decide.
- **No `git commit --amend`** — single-commit pattern for all orchestration state.
