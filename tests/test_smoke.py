"""Basic smoke tests for project scaffolding."""

from pea_met_network import __doc__


def test_package_imports() -> None:
    assert __doc__ is not None
