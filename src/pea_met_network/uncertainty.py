from __future__ import annotations

import pandas as pd


def _risk_band(probability: float) -> str:
    if probability < 0.34:
        return "low"
    if probability < 0.67:
        return "moderate"
    return "high"


def _limitations(overlap_count: int) -> str:
    if overlap_count < 24:
        return "Limited overlap reduces confidence in this estimate."
    return "Sample support is adequate for a coarse uncertainty bound."


def quantify_station_removal_risk(
    benchmark: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in benchmark.to_dict(orient="records"):
        divergence = min(float(row["mean_abs_diff"]) / 1.5, 1.0)
        decorrelation = 1.0 - max(min(float(row["correlation"]), 1.0), 0.0)
        support_penalty = max(0.0, (48 - int(row["overlap_count"])) / 48)
        probability = (0.5 * divergence) + (0.35 * decorrelation)
        probability += 0.15 * support_penalty
        probability = round(min(max(probability, 0.0), 0.95), 2)
        rows.append(
            {
                "station": row["station"],
                "reference_station": row["reference_station"],
                "risk_probability": probability,
                "risk_band": _risk_band(probability),
                "assumptions": (
                    "Risk combines mean divergence, correlation loss, "
                    "and overlap support into a coarse probability bound."
                ),
                "limitations": _limitations(int(row["overlap_count"])),
            }
        )
    return pd.DataFrame(rows)
