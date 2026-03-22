from __future__ import annotations

import pandas as pd

from pea_met_network.uncertainty import quantify_station_removal_risk


def _sample_similarity_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "station": ["alpha", "beta", "gamma"],
            "reference_station": ["stanhope", "stanhope", "stanhope"],
            "overlap_count": [120, 72, 12],
            "mean_abs_diff": [0.15, 0.55, 1.2],
            "correlation": [0.98, 0.83, 0.41],
        }
    )


def test_quantify_station_removal_risk_returns_interpretable_bounds() -> None:
    risk = quantify_station_removal_risk(_sample_similarity_frame())

    assert list(risk["station"]) == ["alpha", "beta", "gamma"]
    assert set(risk.columns) == {
        "station",
        "reference_station",
        "risk_probability",
        "risk_band",
        "assumptions",
        "limitations",
    }
    assert risk.loc[risk["station"] == "alpha", "risk_band"].iloc[0] == "low"
    assert risk.loc[risk["station"] == "gamma", "risk_band"].iloc[0] == "high"
    assert (
        risk.loc[risk["station"] == "alpha", "risk_probability"].iloc[0]
        < risk.loc[risk["station"] == "beta", "risk_probability"].iloc[0]
        < risk.loc[risk["station"] == "gamma", "risk_probability"].iloc[0]
    )


def test_quantify_station_removal_risk_surfaces_sample_size_limitations(
) -> None:
    risk = quantify_station_removal_risk(_sample_similarity_frame())

    gamma_limitations = risk.loc[
        risk["station"] == "gamma", "limitations"
    ].iloc[0]
    alpha_limitations = risk.loc[
        risk["station"] == "alpha", "limitations"
    ].iloc[0]

    assert "limited overlap" in gamma_limitations.lower()
    assert "sample support is adequate" in alpha_limitations.lower()
