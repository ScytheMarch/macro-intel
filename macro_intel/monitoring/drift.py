"""Feature and prediction drift detection using Evidently AI.

Compares reference (historical stable) data to current window
for detecting distributional shifts in macro data and model outputs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DriftConfig:
    """Configuration for drift analysis."""
    reference_months: int = 12      # Size of reference window
    current_months: int = 3         # Size of current window
    country: str = "USA"            # Country to analyze
    feature_families: dict[str, list[str]] | None = None  # Optional grouping


@dataclass
class DriftResult:
    """Results from drift analysis."""
    dataset_drift: bool             # Overall drift detected
    n_drifted_features: int
    n_total_features: int
    drift_share: float              # Fraction of features drifted
    feature_details: dict           # Per-feature drift scores
    report_path: str | None = None  # Path to HTML report


def compute_feature_drift(
    panel: pd.DataFrame,
    config: DriftConfig | None = None,
    output_path: str | Path | None = None,
) -> DriftResult:
    """Run Evidently data drift analysis on feature panel.

    Splits panel into reference and current windows, runs DataDriftPreset.
    """
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset

    if config is None:
        config = DriftConfig()

    # Get single-country data
    try:
        data = panel.xs(config.country, level="country")
    except KeyError:
        logger.error("Country %s not found in panel", config.country)
        return DriftResult(False, 0, 0, 0.0, {})

    if data.empty:
        return DriftResult(False, 0, 0, 0.0, {})

    # Split into reference and current
    dates = data.index.sort_values()
    total_months = config.reference_months + config.current_months

    if len(dates) < total_months:
        logger.warning("Insufficient data for drift analysis (need %d months)", total_months)
        # Use what we have: first 70% reference, last 30% current
        split_idx = int(len(data) * 0.7)
        reference = data.iloc[:split_idx]
        current = data.iloc[split_idx:]
    else:
        cutoff = dates[-config.current_months]
        ref_start = dates[-(config.reference_months + config.current_months)]
        reference = data.loc[ref_start:cutoff].iloc[:-1]
        current = data.loc[cutoff:]

    # Drop columns that are all NaN in either window
    valid_cols = [
        c for c in data.columns
        if reference[c].notna().sum() > 3 and current[c].notna().sum() > 1
    ]
    reference = reference[valid_cols].fillna(method="ffill").dropna()
    current = current[valid_cols].fillna(method="ffill").dropna()

    if reference.empty or current.empty:
        return DriftResult(False, 0, 0, 0.0, {})

    # Reset index for Evidently (it expects numeric index)
    reference = reference.reset_index(drop=True)
    current = current.reset_index(drop=True)

    # Run Evidently drift report
    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=reference, current_data=current)

    # Extract results
    report_dict = report.as_dict()
    metrics = report_dict.get("metrics", [])

    dataset_drift = False
    n_drifted = 0
    n_total = len(valid_cols)
    feature_details = {}

    for metric in metrics:
        result_data = metric.get("result", {})

        if "dataset_drift" in result_data:
            dataset_drift = result_data["dataset_drift"]
            n_drifted = result_data.get("number_of_drifted_columns", 0)

        if "drift_by_columns" in result_data:
            for col_name, col_data in result_data["drift_by_columns"].items():
                feature_details[col_name] = {
                    "drifted": col_data.get("drift_detected", False),
                    "drift_score": col_data.get("drift_score", 0.0),
                    "stattest": col_data.get("stattest_name", ""),
                    "threshold": col_data.get("stattest_threshold", 0.0),
                }

    drift_share = n_drifted / n_total if n_total > 0 else 0.0

    # Save HTML report
    report_path = None
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report.save_html(str(output_path))
        report_path = str(output_path)
        logger.info("Drift report saved to %s", report_path)

    return DriftResult(
        dataset_drift=dataset_drift,
        n_drifted_features=n_drifted,
        n_total_features=n_total,
        drift_share=drift_share,
        feature_details=feature_details,
        report_path=report_path,
    )


def compute_prediction_drift(
    regime_probs_reference: pd.DataFrame,
    regime_probs_current: pd.DataFrame,
    output_path: str | Path | None = None,
) -> DriftResult:
    """Run drift analysis on regime probability predictions.

    Args:
        regime_probs_reference: DataFrame with columns = regime names, reference window
        regime_probs_current: DataFrame with columns = regime names, current window
    """
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset

    if regime_probs_reference.empty or regime_probs_current.empty:
        return DriftResult(False, 0, 0, 0.0, {})

    ref = regime_probs_reference.reset_index(drop=True)
    cur = regime_probs_current.reset_index(drop=True)

    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=ref, current_data=cur)

    report_dict = report.as_dict()
    metrics = report_dict.get("metrics", [])

    dataset_drift = False
    n_drifted = 0
    feature_details = {}

    for metric in metrics:
        result_data = metric.get("result", {})
        if "dataset_drift" in result_data:
            dataset_drift = result_data["dataset_drift"]
            n_drifted = result_data.get("number_of_drifted_columns", 0)

        if "drift_by_columns" in result_data:
            for col_name, col_data in result_data["drift_by_columns"].items():
                feature_details[col_name] = {
                    "drifted": col_data.get("drift_detected", False),
                    "drift_score": col_data.get("drift_score", 0.0),
                }

    n_total = len(regime_probs_reference.columns)
    drift_share = n_drifted / n_total if n_total > 0 else 0.0

    report_path = None
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report.save_html(str(output_path))
        report_path = str(output_path)

    return DriftResult(
        dataset_drift=dataset_drift,
        n_drifted_features=n_drifted,
        n_total_features=n_total,
        drift_share=drift_share,
        feature_details=feature_details,
        report_path=report_path,
    )
