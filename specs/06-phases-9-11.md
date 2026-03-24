# Phases 9-11: Execution, Analysis, and Polish

## Phase 9: Pipeline Execution

### Goal
Run the full data pipeline end-to-end on real PEINP data and produce
materialized outputs in `data/processed/`.

### Acceptance Criteria

| ID | Criterion |
|---|---|
| AC-PIPE-1 | `cleaning.py` runs successfully on all raw data in `data/raw/peinp/` without errors |
| AC-PIPE-2 | Cleaned hourly + daily datasets exist in `data/processed/` for all stations discovered by the manifest |
| AC-PIPE-3 | Imputation report generated — lists all gaps, strategy used, values filled per station |
| AC-PIPE-4 | Stanhope reference data downloaded and cached successfully |
| AC-PIPE-5 | FWI moisture codes (FFMC, DMC, DC) computed for all stations with sufficient data |
| AC-PIPE-6 | Full FWI chain attempted — ISI, BUI, FWI computed where data supports it |
| AC-PIPE-7 | All pipeline artifacts are tracked in a manifest file with timestamps and row counts |

### Exit Gate
```bash
.venv/bin/pytest tests/test_pipeline_execution.py -q
```

### Constraints
- Do not modify library code to pass tests. If the pipeline fails on real data,
  fix the library code (src/) and ensure existing tests still pass.
- Pipeline outputs must be reproducible — running twice should produce the same results.
- `data/processed/` is gitignored. Tests should verify file existence and basic shape,
  not content checksums.

---

## Phase 10: Analysis & Narrative

### Overview
Analysis work is split into four sub-phases to keep each tick focused
and achievable within the iteration budget.

### Sub-Phase 10: EDA + FWI

**Goal:** Implement the exploratory data analysis and fire weather index
sections of the notebook.

| ID | Criterion |
|---|---|
| AC-ANA-1 | Notebook loads real processed data (not stubs) from `data/processed/` |
| AC-ANA-2 | EDA section includes station coverage map/table, temporal coverage summary, and missingness heatmap |
| AC-ANA-6 | FWI section includes time series of moisture codes and fire weather indices for at least 2 stations |
| AC-ANA-8 | All cells execute top-to-bottom without errors |

**Exit Gate:**
```bash
.venv/bin/pytest tests/test_analysis_notebook.py -q
```

### Sub-Phase 10b: PCA + Clustering

**Goal:** Implement the dimensionality reduction and clustering sections.

| ID | Criterion |
|---|---|
| AC-ANA-3 | PCA section includes scree plot, loadings table, and biplot or score plot |
| AC-ANA-4 | Clustering section includes dendrogram or cluster assignment table with intra/inter-cluster distance comparison |
| AC-ANA-8 | All cells execute top-to-bottom without errors |

**Exit Gate:**
```bash
.venv/bin/pytest tests/test_analysis_notebook.py -q
```

### Sub-Phase 10c: Redundancy + Uncertainty

**Goal:** Implement the redundancy verdict and uncertainty quantification.

| ID | Criterion |
|---|---|
| AC-ANA-5 | Redundancy section answers "Which stations are redundant?" with evidence from PCA + clustering + benchmarking |
| AC-ANA-7 | Uncertainty section includes confidence intervals or risk probabilities for station removal recommendations |
| AC-ANA-8 | All cells execute top-to-bottom without errors |

**Exit Gate:**
```bash
.venv/bin/pytest tests/test_analysis_notebook.py -q
```

### Sub-Phase 10d: Conclusion

**Goal:** Write the conclusion and ensure the full notebook runs cleanly.

| ID | Criterion |
|---|---|
| AC-ANA-9 | Notebook has a conclusion cell summarizing key findings and recommendations |
| AC-ANA-8 | All cells execute top-to-bottom without errors |

**Exit Gate:**
```bash
.venv/bin/pytest tests/test_analysis_notebook.py -q
```

### Constraints
- The notebook must use the real processed data from Phase 9, not synthetic data.
- Visualizations should be saved as static images (PNG) in `notebooks/figures/` and
  embedded in the notebook.
- The notebook must answer all four core questions from the project contract.
- Markdown cells must provide interpretation, not just code output.

---

## Phase 11: Final Polish

### Goal
README accurate, repo clean, project ready for submission.

### Acceptance Criteria

| ID | Criterion |
|---|---|
| AC-POL-1 | README reflects actual completed state — all phases done, correct setup instructions, accurate description |
| AC-POL-2 | `__pycache__/` removed from repo and properly gitignored |
| AC-POL-3 | No unexpected files in repo root (repo-shape test passes) |
| AC-POL-4 | `notebooks/analysis.ipynb` is in the correct location per test expectations |
| AC-POL-5 | All 11 done-definition items from `01-project-contract.md` are demonstrably met |
| AC-POL-6 | `pytest` runs the full suite with zero failures |

### Exit Gate
```bash
.venv/bin/pytest -q
```

### Constraints
- Do not modify library logic to pass polish tests.
- If existing tests fail, investigate root cause before patching.
- README must be accurate — no references to "initial planning" or stale status.
