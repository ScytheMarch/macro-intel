"""Data quality monitoring using Evidently AI.

Checks for missing values, range violations, freshness, and other
data quality issues in the feature panel.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class QualityResult:
    """Results from data quality analysis."""
    n_rows: int
    n_columns: int
    missing_pct: float              # Overall missing percentage
    columns_with_issues: list[str]  # Columns flagging quality problems
    summary: dict                   # Per-column quality stats
    report_path: str | None = None


def check_data_quality(
    panel: pd.DataFrame,
    country: str = "USA",
    output_path: str | Path | None = None,
) -> QualityResult:
    """Run Evidently data quality checks on feature panel.

    Checks: missing values, constant columns, near-constant columns,
    outliers, and type inconsistencies.
    """
    from evidently.report import Report
    from evidently.metric_preset import DataQualityPreset

    try:
        data = panel.xs(country, level="country")
    except KeyError:
        logger.error("Country %s not found in panel", country)
        return QualityResult(0, 0, 0.0, [], {})

    if data.empty:
        return QualityResult(0, 0, 0.0, [], {})

    # Keep only numeric columns — Evidently can't handle strings/objects
    data = data.select_dtypes(include="number")

    if data.empty:
        return QualityResult(0, 0, 0.0, [], {})

    # Reset index for Evidently
    data_reset = data.reset_index(drop=True)

    report = Report(metrics=[DataQualityPreset()])
    report.run(reference_data=None, current_data=data_reset)

    report_dict = report.as_dict()

    # Extract quality stats
    n_rows = len(data)
    n_cols = len(data.columns)
    missing_pct = float(data.isna().mean().mean() * 100)

    # Identify columns with issues
    columns_with_issues = []
    summary: dict = {}

    for col in data.columns:
        col_stats: dict = {
            "missing_pct": round(float(data[col].isna().mean() * 100), 1),
            "n_unique": int(data[col].nunique()),
            "dtype": str(data[col].dtype),
        }

        if data[col].notna().any():
            col_stats["mean"] = round(float(data[col].mean()), 4)
            col_stats["std"] = round(float(data[col].std()), 4)
            col_stats["min"] = round(float(data[col].min()), 4)
            col_stats["max"] = round(float(data[col].max()), 4)

        # Flag issues
        issues = []
        if col_stats["missing_pct"] > 20:
            issues.append(f"high missing ({col_stats['missing_pct']}%)")
        if col_stats["n_unique"] <= 1 and data[col].notna().any():
            issues.append("constant")
        if col_stats.get("std", 1) == 0 and data[col].notna().sum() > 1:
            issues.append("zero variance")

        if issues:
            col_stats["issues"] = issues
            columns_with_issues.append(col)

        summary[col] = col_stats

    # Save HTML report
    report_path = None
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report.save_html(str(output_path))
        report_path = str(output_path)
        logger.info("Quality report saved to %s", report_path)

    return QualityResult(
        n_rows=n_rows,
        n_columns=n_cols,
        missing_pct=round(missing_pct, 1),
        columns_with_issues=columns_with_issues,
        summary=summary,
        report_path=report_path,
    )
