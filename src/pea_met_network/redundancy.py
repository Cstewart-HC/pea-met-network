from __future__ import annotations

from pathlib import Path

import pandas as pd


def build_station_matrix(
    frame: pd.DataFrame,
    *,
    value_column: str,
) -> pd.DataFrame:
    matrix = frame.pivot_table(
        index="timestamp_utc",
        columns="station",
        values=value_column,
        aggfunc="mean",
    )
    return matrix.sort_index().sort_index(axis="columns")


def pairwise_station_correlation(matrix: pd.DataFrame) -> pd.DataFrame:
    return matrix.corr(numeric_only=True)


def _zscore_columns(matrix: pd.DataFrame) -> pd.DataFrame:
    centered = matrix - matrix.mean(axis=0)
    scaled = centered / matrix.std(axis=0, ddof=1)
    return scaled.fillna(0.0)


def pca_station_loadings(matrix: pd.DataFrame) -> pd.DataFrame:
    normalized = _zscore_columns(matrix.dropna(axis="index", how="any"))
    import numpy as np

    _, _, vh = np.linalg.svd(
        normalized.to_numpy(),
        full_matrices=False,
    )
    component_count = min(2, vh.shape[0])
    rows: list[dict[str, object]] = []
    for component_index in range(component_count):
        component = f"PC{component_index + 1}"
        for station, loading in zip(
            normalized.columns,
            vh[component_index],
            strict=True,
        ):
            rows.append(
                {
                    "station": station,
                    "component": component,
                    "loading": float(loading),
                }
            )
    return pd.DataFrame(rows)


def cluster_station_order(matrix: pd.DataFrame) -> list[str]:
    reference = matrix.mean(axis=0)
    distances = (matrix - reference).abs().mean(axis=0)
    return distances.sort_values().index.tolist()


def benchmark_to_stanhope(
    matrix: pd.DataFrame,
    *,
    reference_station: str = "stanhope",
) -> pd.DataFrame:
    if reference_station not in matrix.columns:
        raise ValueError(f"Reference station missing: {reference_station}")

    reference = matrix[reference_station]
    rows: list[dict[str, object]] = []
    for station in matrix.columns:
        if station == reference_station:
            continue
        pair = pd.concat([matrix[station], reference], axis=1).dropna()
        rows.append(
            {
                "station": station,
                "reference_station": reference_station,
                "overlap_count": int(len(pair)),
                "mean_abs_diff": float(
                    (pair.iloc[:, 0] - pair.iloc[:, 1]).abs().mean()
                ),
                "correlation": float(pair.iloc[:, 0].corr(pair.iloc[:, 1])),
            }
        )
    return pd.DataFrame(rows)


def _frame_to_markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "(no rows)"
    columns = list(frame.columns)
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = [
        "| " + " | ".join(str(row[column]) for column in columns) + " |"
        for row in frame.to_dict(orient="records")
    ]
    return "\n".join([header, divider, *body])


def write_redundancy_summary(
    frame: pd.DataFrame,
    *,
    value_column: str,
    output_path: Path,
    reference_station: str = "stanhope",
) -> Path:
    matrix = build_station_matrix(frame, value_column=value_column)
    correlation = pairwise_station_correlation(matrix)
    loadings = pca_station_loadings(matrix)
    clustering = cluster_station_order(matrix)
    benchmark = benchmark_to_stanhope(
        matrix,
        reference_station=reference_station,
    )

    sections = [
        "# Redundancy Analysis Summary",
        "",
        "## Correlation",
        _frame_to_markdown_table(correlation.reset_index(names="station")),
        "",
        "## PCA Loadings",
        _frame_to_markdown_table(loadings),
        "",
        "## Clustering Order",
        "\n".join(f"- {station}" for station in clustering),
        "",
        "## Stanhope Benchmark",
        _frame_to_markdown_table(benchmark),
        "",
    ]
    output_path.write_text("\n".join(sections))
    return output_path
