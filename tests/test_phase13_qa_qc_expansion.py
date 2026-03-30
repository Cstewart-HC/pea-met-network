"""Phase 13 tests — QA/QC Report Expansion: Dual-Mode Diagnostics.

Tests for 6 deliverables:
  1. Pre/post imputation missingness snapshots
  2. FWI mode tag in all reports
  3. Compliant mode diagnostics (carry-forward days)
  4. FWI value descriptive statistics
  5. Mode-specific report filenames
  6. Per-stage row count audit in manifest

These tests FAIL until implementation is complete (TDD).
Functions in qa_qc.py already exist — these tests verify pipeline integration.

Exit gate: pytest tests/test_phase13_qa_qc_expansion.py -v
"""
from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hourly(station: str = "stanhope", n: int = 48) -> pd.DataFrame:
    """Create a synthetic hourly DataFrame with all met columns."""
    ts = pd.date_range("2024-07-01", periods=n, freq="h")
    return pd.DataFrame({
        "timestamp_utc": ts,
        "station": station,
        "air_temperature_c": np.random.default_rng(42).uniform(15, 30, n),
        "relative_humidity_pct": np.random.default_rng(43).uniform(30, 80, n),
        "wind_speed_kmh": np.random.default_rng(44).uniform(5, 25, n),
        "rain_mm": np.random.default_rng(45).uniform(0, 5, n),
    })


def _make_daily(station: str = "stanhope", n: int = 3) -> pd.DataFrame:
    """Create a synthetic daily DataFrame with FWI columns."""
    rng = np.random.default_rng(46)
    return pd.DataFrame({
        "timestamp_utc": pd.date_range("2024-07-01", periods=n, freq="D"),
        "station": station,
        "ffmc": rng.uniform(75, 85, n),
        "dmc": rng.uniform(18, 25, n),
        "dc": rng.uniform(95, 110, n),
        "isi": rng.uniform(5, 8, n),
        "bui": rng.uniform(22, 30, n),
        "fwi": rng.uniform(12, 20, n),
    })


def _get_cleaning_source() -> str:
    """Return the source code of cleaning.py for AST inspection."""
    cleaning_path = (
        PROJECT_ROOT / "src" / "pea_met_network" / "cleaning.py"
    )
    return cleaning_path.read_text()


# ===========================================================================
# 1. Pre/Post Imputation Missingness — qa_qc.py functions
# ===========================================================================

class TestPrePostImputationFunctions:
    """Spec 2.1 — pre_imputation_missingness() in qa_qc.py.

    These tests verify the standalone functions exist and work correctly.
    These SHOULD PASS (functions are already implemented).
    """

    def test_function_exists_and_importable(self):
        """pre_imputation_missingness must be importable from qa_qc."""
        from pea_met_network.qa_qc import pre_imputation_missingness
        assert callable(pre_imputation_missingness)

    def test_returns_missing_pct_for_core_variables(self):
        """Must return missing_pct for the 4 core met variables."""
        from pea_met_network.qa_qc import pre_imputation_missingness

        df = _make_hourly()
        df.loc[0:5, "air_temperature_c"] = np.nan
        df.loc[2:3, "relative_humidity_pct"] = np.nan

        result = pre_imputation_missingness(df)

        for var in (
            "air_temperature_c",
            "relative_humidity_pct",
            "wind_speed_kmh",
            "rain_mm",
        ):
            key = f"missing_pct_{var}"
            assert key in result, f"Missing key: {key}"
            assert isinstance(result[key], float)
            assert 0.0 <= result[key] <= 100.0

    def test_returns_zero_when_no_missing(self):
        """All-present data should yield 0.0 for all variables."""
        from pea_met_network.qa_qc import pre_imputation_missingness

        df = _make_hourly()
        result = pre_imputation_missingness(df)

        for var in (
            "air_temperature_c",
            "relative_humidity_pct",
            "wind_speed_kmh",
            "rain_mm",
        ):
            assert result[f"missing_pct_{var}"] == 0.0

    def test_returns_100_when_all_missing(self):
        """All-NaN column should yield 100.0."""
        from pea_met_network.qa_qc import pre_imputation_missingness

        df = _make_hourly()
        df["air_temperature_c"] = np.nan

        result = pre_imputation_missingness(df)
        assert result["missing_pct_air_temperature_c"] == 100.0


# ===========================================================================
# 2.4 FWI Value Statistics — qa_qc.py functions
# ===========================================================================

class TestFWIValueStatisticsFunctions:
    """Spec 2.4 — fwi_descriptive_stats() in qa_qc.py.

    These SHOULD PASS (function is already implemented).
    """

    def test_function_exists_and_importable(self):
        """fwi_descriptive_stats must be importable from qa_qc."""
        from pea_met_network.qa_qc import fwi_descriptive_stats
        assert callable(fwi_descriptive_stats)

    def test_returns_all_24_stats_keys(self):
        """6 FWI codes × 4 stats (min, max, mean, std) = 24 keys."""
        from pea_met_network.qa_qc import fwi_descriptive_stats

        daily = _make_daily()
        result = fwi_descriptive_stats(daily, station="stanhope")

        expected_codes = ["ffmc", "dmc", "dc", "isi", "bui", "fwi"]
        expected_stats = ["min", "max", "mean", "std"]
        for code in expected_codes:
            for stat in expected_stats:
                key = f"{code}_{stat}"
                assert key in result, f"Missing key: {key}"

    def test_std_is_zero_for_constant_values(self):
        """Constant FWI values should yield std=0.0."""
        from pea_met_network.qa_qc import fwi_descriptive_stats

        daily = _make_daily()
        daily["ffmc"] = 85.0
        result = fwi_descriptive_stats(daily, station="stanhope")

        assert result["ffmc_std"] == 0.0
        assert result["ffmc_min"] == 85.0
        assert result["ffmc_max"] == 85.0
        assert result["ffmc_mean"] == 85.0

    def test_stats_correct_for_known_values(self):
        """Verify min/max/mean/std match manual calculation."""
        from pea_met_network.qa_qc import fwi_descriptive_stats

        daily = _make_daily()
        daily["ffmc"] = [10.0, 20.0, 30.0]
        result = fwi_descriptive_stats(daily, station="stanhope")

        assert result["ffmc_min"] == 10.0
        assert result["ffmc_max"] == 30.0
        assert result["ffmc_mean"] == 20.0
        # std(ddof=1): sqrt(((10-20)^2 + (20-20)^2 + (30-20)^2)/2) = 10
        assert abs(result["ffmc_std"] - 10.0) < 0.001


# ===========================================================================
# 2.2 / 2.3 — generate_qa_qc_report() signature tests
# ===========================================================================

class TestGenerateQAQCReportSignature:
    """Tests for generate_qa_qc_report() accepting new parameters.

    These SHOULD PASS (report function already updated).
    """

    def test_fwi_mode_column_in_report(self):
        """fwi_mode column should contain the passed value."""
        from pea_met_network.qa_qc import generate_qa_qc_report

        hourly = _make_hourly()
        daily = _make_daily()
        df = generate_qa_qc_report(hourly, daily, fwi_mode="compliant")
        assert df["fwi_mode"].unique()[0] == "compliant"

    def test_carry_forward_columns_in_compliant_mode(self):
        """Compliant mode report must have carry_forward_days and carry_forward_pct."""
        from pea_met_network.qa_qc import generate_qa_qc_report

        hourly = _make_hourly()
        daily = _make_daily()
        daily["carry_forward_used"] = [False, True, True]

        df = generate_qa_qc_report(hourly, daily, fwi_mode="compliant")

        assert "carry_forward_days" in df.columns
        assert "carry_forward_pct" in df.columns

    def test_pre_imputation_columns_in_report(self):
        """Report must have pre_imp_missing_pct_* columns when data provided."""
        from pea_met_network.qa_qc import generate_qa_qc_report

        hourly = _make_hourly()
        daily = _make_daily()
        pre_imp = {
            "missing_pct_air_temperature_c": 10.0,
            "missing_pct_relative_humidity_pct": 5.0,
            "missing_pct_wind_speed_kmh": 0.0,
            "missing_pct_rain_mm": 2.5,
        }

        df = generate_qa_qc_report(
            hourly, daily,
            pre_imputation_missingness=pre_imp,
        )

        assert "pre_imp_missing_pct_air_temperature_c" in df.columns
        assert df.iloc[0]["pre_imp_missing_pct_air_temperature_c"] == 10.0

    def test_fwi_stats_columns_in_report(self):
        """Report must have ffmc_min, ffmc_max, ffmc_mean, ffmc_std etc."""
        from pea_met_network.qa_qc import generate_qa_qc_report

        hourly = _make_hourly()
        daily = _make_daily()

        df = generate_qa_qc_report(hourly, daily)

        for code in ["ffmc", "dmc", "dc", "isi", "bui", "fwi"]:
            for stat in ["min", "max", "mean", "std"]:
                col = f"{code}_{stat}"
                assert col in df.columns, f"Missing column: {col}"


# ===========================================================================
# PIPELINE INTEGRATION TESTS — These MUST FAIL until Ralph implements
# ===========================================================================

class TestPipelinePreImputationSnapshot:
    """Spec 2.1 — run_pipeline() must capture pre-imputation missingness.

    The pipeline must call pre_imputation_missingness() AFTER enforce_quality
    and BEFORE impute(), then pass the result to generate_qa_qc_report().

    These tests FAIL until cleaning.py is updated.
    """

    def test_pre_imputation_missingness_imported_in_cleaning(self):
        """cleaning.py must import pre_imputation_missingness from qa_qc."""
        source = _get_cleaning_source()
        assert "pre_imputation_missingness" in source, (
            "pre_imputation_missingness not referenced in cleaning.py — "
            "pipeline cannot capture pre-imputation snapshot"
        )

    def test_pre_imputation_missingness_called_in_pipeline(self):
        """run_pipeline() must call pre_imputation_missingness().

        Verify via source inspection that the function is called
        (not just imported) within the per-station processing loop.
        """
        source = _get_cleaning_source()
        # Look for a call pattern like: pre_imputation_missingness(hourly)
        # or pre_imputation_missingness(something)
        call_pattern = r"pre_imputation_missingness\s*\("
        assert re.search(call_pattern, source), (
            "pre_imputation_missingness() is not called in cleaning.py — "
            "pre-imputation snapshot is never captured"
        )

    def test_pre_imputation_data_passed_to_report(self):
        """generate_qa_qc_report() call must include pre_imputation_missingness kwarg.

        The pipeline's call to generate_qa_qc_report must pass the
        pre-imputation snapshot data so it appears in the report.
        """
        source = _get_cleaning_source()
        # The report call should include pre_imputation_missingness= keyword
        call_pattern = (
            r"generate_qa_qc_report\s*\([^)]*"
            r"pre_imputation_missingness\s*="
        )
        assert re.search(call_pattern, source, re.DOTALL), (
            "generate_qa_qc_report() call in cleaning.py does not pass "
            "pre_imputation_missingness= — report will have no pre-imputation data"
        )


class TestPipelineFWIModeInManifest:
    """Spec 2.2 — pipeline manifest must include fwi_mode.

    These tests FAIL until cleaning.py writes fwi_mode to the manifest.
    """

    def test_fwi_mode_written_to_manifest(self):
        """run_pipeline() must write fwi_mode to the manifest dict.

        The manifest JSON should have a top-level 'fwi_mode' key
        reflecting which mode was used for the run.
        """
        source = _get_cleaning_source()
        # Look for manifest["fwi_mode"] or manifest['fwi_mode']
        assert re.search(r'manifest\s*\[\s*["\']fwi_mode["\']\s*\]', source), (
            "manifest['fwi_mode'] not found in cleaning.py — "
            "fwi_mode is not written to pipeline manifest"
        )


class TestPipelineModeSpecificFilenames:
    """Spec 2.5 — pipeline writes to mode-specific report filenames.

    These SHOULD PASS (already implemented in cleaning.py).
    Kept as regression guards.
    """

    def test_qa_qc_report_uses_mode_suffix(self):
        """QA/QC report path must include fwi_mode suffix."""
        source = _get_cleaning_source()
        assert re.search(
            r'qa_qc_report_.*fwi_mode.*\.csv',
            source,
        ), (
            "qa_qc_report filename does not use fwi_mode suffix"
        )

    def test_fwi_missingness_report_uses_mode_suffix(self):
        """FWI missingness report path must include fwi_mode suffix."""
        source = _get_cleaning_source()
        assert re.search(
            r'fwi_missingness_report_.*fwi_mode.*\.csv',
            source,
        ), (
            "fwi_missingness_report filename does not use fwi_mode suffix"
        )


class TestPipelinePerStageRowCounts:
    """Spec 2.6 — stage_row_counts in pipeline manifest.

    These SHOULD PASS (already implemented in cleaning.py).
    Kept as regression guards.
    """

    def test_stage_row_counts_initialized(self):
        """stage_row_counts must be initialized in run_pipeline."""
        source = _get_cleaning_source()
        assert "stage_row_counts" in source, (
            "stage_row_counts not found in cleaning.py"
        )

    def test_stage_row_counts_has_all_seven_stages(self):
        """All 7 pipeline stages must be tracked."""
        source = _get_cleaning_source()
        expected_stages = [
            "raw", "deduped", "hourly", "truncated",
            "post_quality", "post_imputation", "post_cross_station",
        ]
        for stage in expected_stages:
            assert f'"{stage}"' in source, (
                f'Stage "{stage}" not found in cleaning.py'
            )

    def test_stage_row_counts_written_to_manifest(self):
        """stage_row_counts must be written to the manifest dict."""
        source = _get_cleaning_source()
        assert re.search(
            r'manifest\s*\[\s*["\']stage_row_counts["\']\s*\]',
            source,
        ), (
            "manifest['stage_row_counts'] not found in cleaning.py"
        )


# ===========================================================================
# MANIFEST CONTENT TESTS — Require actual pipeline run
# ===========================================================================

class TestManifestContentAfterRun:
    """Tests that verify manifest content from an actual pipeline run.

    These are skipped if no manifest exists (no pipeline run yet).
    They verify the integration end-to-end.
    """

    def test_fwi_mode_key_in_manifest(self):
        """Pipeline manifest must have fwi_mode key."""
        import json

        manifest_path = (
            PROJECT_ROOT / "data" / "processed" / "pipeline_manifest.json"
        )
        if not manifest_path.exists():
            pytest.skip("No pipeline manifest — run pipeline first")

        manifest = json.loads(manifest_path.read_text())
        assert "fwi_mode" in manifest, (
            "fwi_mode key missing from pipeline manifest"
        )
        assert manifest["fwi_mode"] in ("hourly", "compliant"), (
            f"fwi_mode has unexpected value: {manifest['fwi_mode']!r}"
        )

    def test_stage_row_counts_key_in_manifest(self):
        """Pipeline manifest must have stage_row_counts per station."""
        import json

        manifest_path = (
            PROJECT_ROOT / "data" / "processed" / "pipeline_manifest.json"
        )
        if not manifest_path.exists():
            pytest.skip("No pipeline manifest — run pipeline first")

        manifest = json.loads(manifest_path.read_text())
        assert "stage_row_counts" in manifest, (
            "stage_row_counts key missing from manifest"
        )

    def test_stage_row_counts_has_expected_stages(self):
        """stage_row_counts must have all 7 pipeline stage keys."""
        import json

        manifest_path = (
            PROJECT_ROOT / "data" / "processed" / "pipeline_manifest.json"
        )
        if not manifest_path.exists():
            pytest.skip("No pipeline manifest — run pipeline first")

        manifest = json.loads(manifest_path.read_text())
        stage_counts = manifest["stage_row_counts"]

        assert isinstance(stage_counts, dict)

        for station, stages in stage_counts.items():
            expected_stages = [
                "raw", "deduped", "hourly", "truncated",
                "post_quality", "post_imputation", "post_cross_station",
            ]
            for stage in expected_stages:
                assert stage in stages, (
                    f"Missing stage '{stage}' for {station}"
                )
            break  # only check one station

    def test_stage_row_counts_values_are_integers(self):
        """All stage row counts must be non-negative integers."""
        import json

        manifest_path = (
            PROJECT_ROOT / "data" / "processed" / "pipeline_manifest.json"
        )
        if not manifest_path.exists():
            pytest.skip("No pipeline manifest — run pipeline first")

        manifest = json.loads(manifest_path.read_text())
        stage_counts = manifest["stage_row_counts"]

        for station, stages in stage_counts.items():
            for stage, count in stages.items():
                assert isinstance(count, int), (
                    f"{station}.{stage} = {count!r} is not int"
                )
                assert count >= 0, (
                    f"{station}.{stage} = {count} is negative"
                )
