"""Data quality monitoring using pandas/numpy.

Checks for missing values, range violations, freshness, and other
data quality issues in the feature panel.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class QualityResult:
    """Results from data quality analysis."""
    n_rows: int
    n_columns: int
    missing_pct: float
    columns_with_issues: list[str] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    report_path: str | None = None


def check_data_quality(
    panel: pd.DataFrame,
    country: str = "USA",
    output_path: str | Path | None = None,
) -> QualityResult:
    """Run data quality checks on feature panel.

    Checks: missing values, constant columns, zero variance,
    outliers, and stale data.
    """
    try:
        data = panel.xs(country, level="country")
    except KeyError:
        logger.error("Country %s not found in panel", country)
        return QualityResult(0, 0, 0.0, [], {})

    if data.empty:
        return QualityResult(0, 0, 0.0, [], {})

    # Keep only numeric columns
    data = data.select_dtypes(include="number")

    if data.empty:
        return QualityResult(0, 0, 0.0, [], {})

    n_rows = len(data)
    n_cols = len(data.columns)
    missing_pct = float(data.isna().mean().mean() * 100)

    columns_with_issues = []
    summary: dict = {}

    for col in data.columns:
        col_series = data[col]
        n_missing = int(col_series.isna().sum())
        col_missing_pct = round(float(col_series.isna().mean() * 100), 1)
        n_unique = int(col_series.nunique())

        col_stats: dict = {
            "missing_pct": col_missing_pct,
            "n_missing": n_missing,
            "n_unique": n_unique,
            "dtype": str(col_series.dtype),
        }

        if col_series.notna().any():
            vals = col_series.dropna()
            col_stats["mean"] = round(float(vals.mean()), 4)
            col_stats["std"] = round(float(vals.std()), 4)
            col_stats["min"] = round(float(vals.min()), 4)
            col_stats["max"] = round(float(vals.max()), 4)
            col_stats["latest"] = round(float(vals.iloc[-1]), 4) if len(vals) > 0 else None

            # Check for outliers (values beyond 4 std devs)
            if col_stats["std"] > 0:
                z_scores = np.abs((vals - vals.mean()) / vals.std())
                n_outliers = int((z_scores > 4).sum())
                col_stats["n_outliers"] = n_outliers
            else:
                col_stats["n_outliers"] = 0

            # Check staleness — is the last non-NaN value old?
            last_valid_idx = col_series.last_valid_index()
            if last_valid_idx is not None and hasattr(last_valid_idx, 'date'):
                days_stale = (data.index.max() - last_valid_idx).days
                col_stats["days_since_update"] = days_stale
            else:
                col_stats["days_since_update"] = 0

        # Flag issues
        issues = []
        if col_missing_pct > 20:
            issues.append(f"high missing ({col_missing_pct}%)")
        if n_unique <= 1 and col_series.notna().any():
            issues.append("constant")
        if col_stats.get("std", 1) == 0 and col_series.notna().sum() > 1:
            issues.append("zero variance")
        if col_stats.get("n_outliers", 0) > 3:
            issues.append(f"{col_stats['n_outliers']} outliers")
        if col_stats.get("days_since_update", 0) > 90:
            issues.append(f"stale ({col_stats['days_since_update']}d)")

        if issues:
            col_stats["issues"] = issues
            columns_with_issues.append(col)

        summary[col] = col_stats

    return QualityResult(
        n_rows=n_rows,
        n_columns=n_cols,
        missing_pct=round(missing_pct, 1),
        columns_with_issues=columns_with_issues,
        summary=summary,
        report_path=None,
    )
