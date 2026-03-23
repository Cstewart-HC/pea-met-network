from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde


def _risk_band(probability: float) -> str:
    if probability < 0.25:
        return "low"
    if probability < 0.6:
        return "moderate"
    return "high"


def _limitations(overlap_count: int) -> str:
    if overlap_count < 24:
        return (
            "Insufficient overlap for reliable uncertainty estimation; "
            "intervals are intentionally wide."
        )
    return "Sample support is adequate for a coarse uncertainty bound."


def _clip_probability(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _sample_upper_bound(observations: np.ndarray) -> float:
    finite = np.asarray(observations, dtype=float)
    finite = finite[np.isfinite(finite)]
    finite = finite[finite >= 0.0]
    if finite.size == 0:
        return 1.0

    empirical_q95 = float(np.quantile(finite, 0.95))
    empirical_max = float(np.max(finite))
    return max(empirical_q95, empirical_max)


def _synthetic_observations(
    *,
    mean_abs_diff: float,
    correlation: float,
    overlap_count: int,
) -> np.ndarray:
    support = max(int(overlap_count), 8)
    decorrelation = 1.0 - float(np.clip(correlation, 0.0, 1.0))
    center = float(mean_abs_diff)
    spread = max(0.03, center * 0.2) + (0.6 * decorrelation)
    spread *= np.sqrt(24.0 / max(float(overlap_count), 24.0))
    offsets = np.linspace(-1.0, 1.0, support)
    samples = center + (offsets * spread)
    return np.clip(samples, 0.0, 1.0)


def _distribution_samples(
    *,
    observations: np.ndarray,
    sample_size: int = 256,
) -> np.ndarray:
    observed = np.asarray(observations, dtype=float)
    finite = observed[np.isfinite(observed)]
    finite = finite[finite >= 0.0]
    if finite.size == 0:
        return np.full(sample_size, 0.5)
    if finite.size == 1 or np.allclose(finite, finite[0]):
        value = float(finite[0])
        return np.full(sample_size, value)

    kde = gaussian_kde(finite)
    sampled = kde.resample(sample_size, seed=0).reshape(-1)

    upper = _sample_upper_bound(finite)
    sampled = np.clip(sampled, 0.0, upper)
    if upper > 1.0:
        sampled = sampled / upper

    return sampled



def quantify_station_removal_risk(
    benchmark: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in benchmark.to_dict(orient="records"):
        observations = row.get("observations")
        if observations is None:
            observations = _synthetic_observations(
                mean_abs_diff=float(row["mean_abs_diff"]),
                correlation=float(row["correlation"]),
                overlap_count=int(row["overlap_count"]),
            )
        samples = _distribution_samples(
            observations=np.asarray(observations, dtype=float),
        )
        probability = _clip_probability(float(np.mean(samples)))
        ci_lower, ci_upper = np.quantile(samples, [0.1, 0.9])
        ci_lower = _clip_probability(float(ci_lower))
        ci_upper = _clip_probability(float(ci_upper))
        rows.append(
            {
                "station": row["station"],
                "reference_station": row["reference_station"],
                "risk_probability": probability,
                "ci_lower": float(ci_lower),
                "ci_upper": float(ci_upper),
                "risk_band": _risk_band(probability),
                "assumptions": (
                    "Distributional uncertainty is estimated with "
                    "scipy.stats.gaussian_kde over observation-derived "
                    "station-reference divergence samples; when benchmark "
                    "fixtures omit raw observations, a documented synthetic "
                    "distribution is generated from mean difference, "
                    "correlation, and overlap support."
                ),
                "limitations": _limitations(int(row["overlap_count"])),
            }
        )
    return pd.DataFrame(rows)
