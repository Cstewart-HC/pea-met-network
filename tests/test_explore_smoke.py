"""Smoke test for the Phase 3 explore notebook.

AC-REM-6: Verify the explore notebook exists and executes without errors
on the cleaned test data.
"""

from pathlib import Path

import pytest
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

NOTEBOOK_PATH = (
    Path(__file__).resolve().parents[1] / "notebooks" / "01_explore.ipynb"
)
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"


def test_notebook_file_exists():
    """The explore notebook file must exist."""
    assert NOTEBOOK_PATH.is_file(), (
        f"Explore notebook not found at {NOTEBOOK_PATH}"
    )


def test_notebook_is_valid_json():
    """The notebook must be parseable as a valid Jupyter notebook."""
    nb = nbformat.read(str(NOTEBOOK_PATH), as_version=4)
    assert nb.cells, "Notebook has no cells"
    ks = nb.metadata.get("kernelspec")
    assert ks and ks.get("language") == "python", (
        "Notebook kernel must be Python"
    )


@pytest.mark.e2e
def test_notebook_executes_without_error():
    """The notebook must execute end-to-end on cleaned data without errors."""
    nb = nbformat.read(str(NOTEBOOK_PATH), as_version=4)
    ep = ExecutePreprocessor(
        timeout=120,
        kernel_name="python3",
        resources={"metadata": {"path": str(NOTEBOOK_PATH.parent.parent)}},
    )
    ep.preprocess(nb, {"metadata": {"path": str(NOTEBOOK_PATH.parent.parent)}})
