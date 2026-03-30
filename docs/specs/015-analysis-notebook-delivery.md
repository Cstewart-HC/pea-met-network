# Phase 15 — Analysis Notebook Delivery

**Status:** proposed  
**Branch:** `feature/phase15-analysis-notebook`  
**Depends on:** Phases 1–14 (all merged to `main`)

---

## Problem

The end-user analysis notebook (`analysis.ipynb`) is stale — written during early development, it has no awareness of the two-mode FWI system (hourly / compliant), doesn't ingest any Phase 13 QA/QC reports or Phase 14 chain break diagnostics, and the conclusion section is blank. Two other notebooks (`analysis_executed.ipynb`, `notebooks/01_explore.ipynb`) are dead artifacts.

## Scope

### Deletions
| File | Reason |
|---|---|
| `analysis_executed.ipynb` | Stale cached outputs, confusing duplicate of `analysis.ipynb` |
| `notebooks/01_explore.ipynb` | Phase 3 artifact, fully subsumed by Section 2 of `analysis.ipynb` |

### Notebook Restructure

Rewrite `analysis.ipynb` with the following sections. Each section is self-contained (can run independently after Cell 0).

#### Cell 0 — Configuration & Imports
- FWI mode selector: `FWI_MODE = "hourly"` (default) or `"compliant"`
- All imports (pandas, matplotlib, seaborn, sklearn, project modules)
- Path constants: `PROCESSED_DIR`, `FIGURES_DIR`
- Seaborn style, figure DPI
- `ANALYSIS_START` date range (from cleaning-config.json)

#### Section 1 — Data Loading
- Load hourly CSVs from `data/processed/{station}/station_hourly.csv`
- Load daily CSVs from `data/processed/{station}/station_daily.csv`
- Print row counts per station
- **No changes needed** — existing logic works, just ensure station detection is robust

#### Section 2 — Exploratory Data Analysis (existing, minor updates)
- 2.1 Coverage table — **unchanged**
- 2.2 Temporal coverage plot — **unchanged**
- 2.3 Missingness heatmap — add FWI columns (`ffmc`, `dmc`, `dc`, `isi`, `bui`, `fwi`) to the variable list
- 2.4 **NEW: Imputation Summary** — read `data/processed/imputation_report.csv`, display:
  - Gaps filled per station per variable
  - Imputation method breakdown (linear, cross-station, carry-forward)
  - Summary bar chart: total gaps filled by station

#### Section 3 — Fire Weather Index Analysis (major rewrite)
- 3.1 **FWI Component Time Series** — update to plot all 6 stations (currently only top 2), use daily means for DC/DMC/BUI/FWI and hourly for FFMC
- 3.2 **NEW: FWI Mode Comparison** — when both hourly and compliant CSVs exist, overlay FWI values from both modes on a single plot for each station. Show divergence where they differ (e.g., during chain breaks)
- 3.3 **NEW: FWI Value Statistics** — read `fwi_descriptive_stats` from QA/QC report (min/max/mean/std per code per station). Display as styled table.
- 3.4 **NEW: Chain Break Analysis** — read `data/processed/fwi_missingness_report_{mode}.csv`:
  - Summary table: breaks per station, grouped by cause (`input_missing` vs `startup`)
  - Breakdown by missing input (RH dominant, temp, etc.)
  - Bar chart: chain breaks by station, colored by cause
  - Cascade origins table (for cascade breaks)

#### Section 4 — Data Quality Report (new section)
- Read `data/processed/qa_qc_report_{mode}.csv` (Phase 13 output)
- **Known bug:** QA/QC report may not exist for hourly mode — `_collect_qa_qc_data()` returns empty. Fix as part of this phase.
- 4.1 **Pre/Post Imputation Missingness** — side-by-side comparison showing how much each variable improved
- 4.2 **Quality Enforcement Actions** — read `quality_enforcement_report.csv`, show count by action type and station
- 4.3 **Out-of-Range Summary** — from QA/QC report: OOR counts for temp, RH, wind per station
- 4.4 **Cross-Station Imputation Audit** — read `cross_station_imputation_audit.csv`, show donor→recipient pairs and count

#### Section 5 — PCA (existing, unchanged)
- 5.1 Station matrix, loadings
- 5.2 Scree plot
- 5.3 Biplot

#### Section 6 — Hierarchical Clustering (existing, unchanged)
- 6.1 Dendrogram
- 6.2 Cluster assignments + pairwise distance matrix

#### Section 7 — Redundancy Analysis (existing, unchanged)
- 7.1 Stanhope benchmark
- 7.2 Station recommendations

#### Section 8 — Uncertainty Quantification (existing, unchanged)
- 8.1 Removal risk with confidence intervals

#### Section 9 — Conclusion
- **Left blank** — to be written by the end user after reviewing all analysis sections
- Include an empty markdown cell with a brief placeholder: `"# Conclusion\n\n_TBD — fill in after review._"`

### Bug Fix: QA/QC Report Generation for Hourly Mode

The `_collect_qa_qc_data()` function in `cleaning.py` returns empty for hourly mode, so no `qa_qc_report_hourly.csv` is written. Investigation needed — likely the daily file detection logic fails for hourly mode's daily output path. Fix as part of this phase so Section 4 of the notebook has data.

## Files Changed
| File | Action |
|---|---|
| `analysis.ipynb` | Rewrite (Sections 2.3, 3, 9 major; Sections 4, 8 new) |
| `analysis_executed.ipynb` | Delete |
| `notebooks/01_explore.ipynb` | Delete |
| `src/pea_met_network/cleaning.py` | Fix `_collect_qa_qc_data()` for hourly mode |
| `src/pea_met_network/qa_qc.py` | Minor: verify column names match notebook expectations |

## Acceptance Criteria
1. [ ] `analysis_executed.ipynb` and `01_explore.ipynb` deleted
2. [ ] `analysis.ipynb` runs end-to-end with no errors on fresh kernel
3. [ ] FWI mode selector works — switching between `hourly` and `compliant` loads correct data
4. [ ] Chain break report ingested and visualized (Section 3.4)
5. [ ] QA/QC report generated for hourly mode (bug fix)
6. [ ] Imputation summary section populated from `imputation_report.csv`
7. [ ] All existing sections (PCA, clustering, redundancy, uncertainty) still work
8. [ ] Conclusion section left blank for user to fill in
9. [ ] No hardcoded station lists — all derived from disk

## Out of Scope
- Interactive widgets / dashboards (static notebook only)
- Export to PDF/HTML (user can do this via nbconvert)
- New analytical methods (PCA, clustering etc. are sufficient)
- Changes to the FWI calculation pipeline itself
