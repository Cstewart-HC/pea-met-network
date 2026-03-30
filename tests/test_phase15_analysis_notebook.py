#!/usr/bin/env python3
"""Phase 15 tests — Analysis Notebook Delivery.

Tests for stale notebook deletion, notebook structure, QA/QC bug fix,
data ingestion, and absence of hardcoded station lists.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_notebook() -> dict:
    """Load analysis.ipynb as JSON dict."""
    nb_path = PROJECT_ROOT / "analysis.ipynb"
    assert nb_path.exists(), "analysis.ipynb must exist"
    return json.loads(nb_path.read_text())


def _cell_sources(nb: dict) -> list[str]:
    """Return list of joined cell source strings."""
    return ["".join(c["source"]) for c in nb["cells"]]


def _markdown_cells(nb: dict) -> list[str]:
    """Return source strings for markdown cells only."""
    return [
        "".join(c["source"])
        for c in nb["cells"]
        if c["cell_type"] == "markdown"
    ]


def _code_cells(nb: dict) -> list[str]:
    """Return source strings for code cells only."""
    return [
        "".join(c["source"])
        for c in nb["cells"]
        if c["cell_type"] == "code"
    ]


# ---------------------------------------------------------------------------
# 1. Stale Notebook Deletion
# ---------------------------------------------------------------------------


class TestP15_StaleNotebookDeletion:
    """Stale notebooks must be deleted."""

    def test_analysis_executed_notebook_deleted(self):
        path = PROJECT_ROOT / "analysis_executed.ipynb"
        assert not path.exists(), (
            "analysis_executed.ipynb must be deleted"
        )

    def test_explore_notebook_deleted(self):
        path = PROJECT_ROOT / "notebooks" / "01_explore.ipynb"
        assert not path.exists(), (
            "notebooks/01_explore.ipynb must be deleted"
        )


# ---------------------------------------------------------------------------
# 2. Notebook Structure — Cell 0 Configuration
# ---------------------------------------------------------------------------


class TestP15_NotebookCell0:
    """Cell 0 must have FWI_MODE selector and core imports."""

    def test_cell0_has_fwi_mode(self):
        nb = _load_notebook()
        src = _code_cells(nb)[0]
        assert "FWI_MODE" in src, "Cell 0 must define FWI_MODE"
        assert '"hourly"' in src, "Cell 0 must default FWI_MODE to 'hourly'"

    def test_cell0_has_processed_dir(self):
        nb = _load_notebook()
        src = _code_cells(nb)[0]
        assert "PROCESSED_DIR" in src, "Cell 0 must define PROCESSED_DIR"

    def test_cell0_has_figures_dir(self):
        nb = _load_notebook()
        src = _code_cells(nb)[0]
        assert "FIGURES_DIR" in src, "Cell 0 must define FIGURES_DIR"


# ---------------------------------------------------------------------------
# 3. Notebook Section Presence
# ---------------------------------------------------------------------------


class TestP15_NotebookSections:
    """All required sections must be present as markdown headings."""

    def test_section_data_loading(self):
        md = _markdown_cells(_load_notebook())
        assert any("Data Loading" in c for c in md), (
            "Missing 'Data Loading' section"
        )

    def test_section_imputation_summary(self):
        md = _markdown_cells(_load_notebook())
        assert any("Imputation Summary" in c for c in md), (
            "Missing 'Imputation Summary' section (2.4)"
        )

    def test_section_fwi_mode_comparison(self):
        md = _markdown_cells(_load_notebook())
        assert any("FWI Mode Comparison" in c for c in md), (
            "Missing 'FWI Mode Comparison' section (3.2)"
        )

    def test_section_fwi_value_statistics(self):
        md = _markdown_cells(_load_notebook())
        assert any("FWI Value Statistics" in c for c in md), (
            "Missing 'FWI Value Statistics' section (3.3)"
        )

    def test_section_chain_break_analysis(self):
        md = _markdown_cells(_load_notebook())
        assert any("Chain Break Analysis" in c for c in md), (
            "Missing 'Chain Break Analysis' section (3.4)"
        )

    def test_section_data_quality_report(self):
        md = _markdown_cells(_load_notebook())
        assert any("Data Quality Report" in c for c in md), (
            "Missing 'Data Quality Report' section (4)"
        )

    def test_section_pca(self):
        md = _markdown_cells(_load_notebook())
        assert any("Principal Component" in c or "PCA" in c for c in md), (
            "Missing PCA section"
        )

    def test_section_clustering(self):
        md = _markdown_cells(_load_notebook())
        assert any("Hierarchical Clustering" in c for c in md), (
            "Missing Hierarchical Clustering section"
        )

    def test_section_redundancy(self):
        md = _markdown_cells(_load_notebook())
        assert any("Redundancy" in c for c in md), (
            "Missing Redundancy Analysis section"
        )

    def test_section_uncertainty(self):
        md = _markdown_cells(_load_notebook())
        assert any("Uncertainty" in c for c in md), (
            "Missing Uncertainty Quantification section"
        )

    def test_section_conclusion_blank(self):
        md = _markdown_cells(_load_notebook())
        conclusion_cells = [c for c in md if "Conclusion" in c]
        assert len(conclusion_cells) >= 1, "Missing Conclusion section"
        # The last Conclusion cell must have TBD placeholder
        last = conclusion_cells[-1]
        assert "TBD" in last, (
            "Conclusion section must contain 'TBD' placeholder"
        )


# ---------------------------------------------------------------------------
# 4. Missingness Heatmap includes FWI columns
# ---------------------------------------------------------------------------


class TestP15_MissingnessHeatmap:
    """Section 2.3 heatmap must include FWI columns."""

    def test_heatmap_includes_fwi_columns(self):
        nb = _load_notebook()
        all_src = _cell_sources(nb)
        # Find the code cell after the 2.3 markdown heading
        combined = "\n".join(all_src)
        # The heatmap section should define a variable list with FWI cols
        # Check that FWI columns appear in a list near the heatmap code
        fwi_cols = ["ffmc", "dmc", "dc", "isi", "bui", "fwi"]
        for col in fwi_cols:
            # Must appear in a code cell (not just as a plot label)
            code_combined = "\n".join(_code_cells(nb))
            assert col in code_combined, (
                f"FWI column '{col}' must appear in notebook code cells"
            )


# ---------------------------------------------------------------------------
# 5. FWI Time Series plots all 6 stations
# ---------------------------------------------------------------------------


class TestP15_FWITimeSeries:
    """Section 3.1 must plot all stations, not just top 2."""

    def test_fwi_plots_all_stations(self):
        nb = _load_notebook()
        code = _code_cells(nb)
        # The old notebook had code like: fwi_sorted = sorted(..., key=...)[:2]
        # The new one should NOT limit to 2 stations
        combined = "\n".join(code)
        # Should not have a slice [:2] on the FWI station list
        assert "[:2]" not in combined, (
            "FWI section must not limit to 2 stations with [:2]"
        )


# ---------------------------------------------------------------------------
# 6. Imputation Summary reads from imputation_report.csv
# ---------------------------------------------------------------------------


class TestP15_ImputationSummary:
    """Section 2.4 must read imputation_report.csv."""

    def test_reads_imputation_report(self):
        nb = _load_notebook()
        code = "\n".join(_code_cells(nb))
        assert "imputation_report" in code, (
            "Notebook must read imputation_report.csv"
        )


# ---------------------------------------------------------------------------
# 7. Chain Break Analysis reads from fwi_missingness_report
# ---------------------------------------------------------------------------


class TestP15_ChainBreakIngestion:
    """Section 3.4 must read fwi_missingness_report_{mode}.csv."""

    def test_reads_chain_break_report(self):
        nb = _load_notebook()
        code = "\n".join(_code_cells(nb))
        assert "fwi_missingness_report" in code, (
            "Notebook must read fwi_missingness_report_{mode}.csv"
        )


# ---------------------------------------------------------------------------
# 8. Data Quality Report reads from qa_qc_report
# ---------------------------------------------------------------------------


class TestP15_QAQCIngestion:
    """Section 4 must read qa_qc_report_{mode}.csv."""

    def test_reads_qa_qc_report(self):
        nb = _load_notebook()
        code = "\n".join(_code_cells(nb))
        assert "qa_qc_report" in code, (
            "Notebook must read qa_qc_report_{mode}.csv"
        )


# ---------------------------------------------------------------------------
# 9. Cross-Station Imputation Audit
# ---------------------------------------------------------------------------


class TestP15_CrossStationAudit:
    """Section 4 must read cross_station_imputation_audit.csv."""

    def test_reads_cross_station_audit(self):
        nb = _load_notebook()
        code = "\n".join(_code_cells(nb))
        assert "cross_station_imputation_audit" in code, (
            "Notebook must read cross_station_imputation_audit.csv"
        )


# ---------------------------------------------------------------------------
# 10. No Hardcoded Station Lists
# ---------------------------------------------------------------------------


class TestP15_NoHardcodedStations:
    """Station lists must be derived from disk, not hardcoded."""

    def test_no_hardcoded_station_list(self):
        nb = _load_notebook()
        code = "\n".join(_code_cells(nb))
        # The old notebook had: stations = sorted(["greenwich", "cavendish", ...])
        # The new one should derive from PROCESSED_DIR.iterdir()
        # Check that the 6-station literal list does NOT appear
        hardcoded = (
            '["greenwich", "cavendish", "north_rustico", '
            '"stanley_bridge", "tracadie", "stanhope"]'
        )
        assert hardcoded not in code, (
            "Station list must not be hardcoded — derive from disk"
        )
        # Also check the tuple variant
        hardcoded2 = (
            '("greenwich", "cavendish", "north_rustico", '
            '"stanley_bridge", "tracadie", "stanhope")'
        )
        assert hardcoded2 not in code, (
            "Station list must not be hardcoded — derive from disk"
        )


# ---------------------------------------------------------------------------
# 11. QA/QC Bug Fix — _collect_qa_qc_data
# ---------------------------------------------------------------------------


class TestP15_CollectQAQCData:
    """_collect_qa_qc_data must load from disk even when all stations
    are in current_stations (the current bug)."""

    @pytest.fixture
    def processed_dir(self, tmp_path):
        """Create a fake PROCESSED_DIR with one station's data."""
        station_dir = tmp_path / "stanhope"
        station_dir.mkdir()
        # Minimal hourly CSV
        hourly = pd.DataFrame({
            "timestamp_utc": pd.date_range("2023-06-01", periods=24, freq="h"),
            "air_temperature_c": 20.0,
            "relative_humidity_pct": 60.0,
            "wind_speed_kmh": 10.0,
            "rain_mm": 0.0,
            "station": "stanhope",
        })
        hourly.to_csv(station_dir / "station_hourly.csv", index=False)
        # Minimal daily CSV
        daily = pd.DataFrame({
            "timestamp_utc": pd.date_range("2023-06-01", periods=1, freq="D"),
            "air_temperature_c": 20.0,
            "station": "stanhope",
        })
        daily.to_csv(station_dir / "station_daily.csv", index=False)
        return tmp_path

    def test_loads_from_disk_when_current_stations_match(
        self, processed_dir
    ):
        """Bug: passing all stations in current_stations with empty
        current_hourly/daily returns nothing. Fix: must load from disk."""
        from pea_met_network.cleaning import _collect_qa_qc_data

        with patch(
            "pea_met_network.cleaning.PROCESSED_DIR", processed_dir
        ), patch(
            "pea_met_network.cleaning.ALL_STATIONS",
            ["stanhope"],
        ):
            all_h, all_d = _collect_qa_qc_data(
                current_hourly=[],
                current_daily=[],
                current_stations=["stanhope"],
            )
            assert len(all_h) > 0, (
                "_collect_qa_qc_data must load stanhope hourly from disk "
                "even when stanhope is in current_stations"
            )
            assert len(all_d) > 0, (
                "_collect_qa_qc_data must load stanhope daily from disk "
                "even when stanhope is in current_stations"
            )

    def test_returns_empty_when_no_disk_files(self, tmp_path):
        """No files on disk → empty lists."""
        from pea_met_network.cleaning import _collect_qa_qc_data

        with patch(
            "pea_met_network.cleaning.PROCESSED_DIR", tmp_path
        ), patch(
            "pea_met_network.cleaning.ALL_STATIONS",
            ["nonexistent"],
        ):
            all_h, all_d = _collect_qa_qc_data(
                current_hourly=[],
                current_daily=[],
                current_stations=["nonexistent"],
            )
            assert len(all_h) == 0
            assert len(all_d) == 0


# ---------------------------------------------------------------------------
# 12. Quality Enforcement Report ingestion
# ---------------------------------------------------------------------------


class TestP15_QualityEnforcementIngestion:
    """Section 4 must read quality_enforcement_report.csv."""

    def test_reads_quality_enforcement_report(self):
        nb = _load_notebook()
        code = "\n".join(_code_cells(nb))
        assert "quality_enforcement_report" in code, (
            "Notebook must read quality_enforcement_report.csv"
        )


# ---------------------------------------------------------------------------
# 13. FWI Mode Selector used in data loading paths
# ---------------------------------------------------------------------------


class TestP15_FWIModeInPaths:
    """FWI_MODE must be used in file paths for mode-specific reports."""

    def test_fwi_mode_used_in_report_paths(self):
        nb = _load_notebook()
        code = "\n".join(_code_cells(nb))
        # At least one report path should use FWI_MODE for interpolation
        assert f"{{FWI_MODE}}" in code or "f\"qa_qc_report_{FWI_MODE}" in code or "f'qa_qc_report_{FWI_MODE}" in code, (
            "Report file paths must use FWI_MODE variable for mode-specific files"
        )
