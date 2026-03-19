"""Feature drift detection using scipy statistical tests.

Compares reference (historical stable) data to current window
for detecting distributional shifts in macro data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DriftConfig:
    """Configuration for drift analysis."""
    reference_months: int = 12
    current_months: int = 3
    country: str = "USA"
    p_value_threshold: float = 0.05  # Below this = drift detected
    feature_families: dict[str, list[str]] | None = None


@dataclass
class DriftResult:
    """Results from drift analysis."""
    dataset_drift: bool
    n_drifted_features: int
    n_total_features: int
    drift_share: float
    feature_details: dict = field(default_factory=dict)
    report_path: str | None = None


def compute_feature_drift(
    panel: pd.DataFrame,
    config: DriftConfig | None = None,
    output_path: str | Path | None = None,
) -> DriftResult:
    """Run statistical drift analysis using KS-test and t-test.

    Splits panel into reference and current windows, tests each feature.
    """
    from scipy import stats

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

    # Keep only numeric columns
    data = data.select_dtypes(include="number")
    if data.empty:
        return DriftResult(False, 0, 0, 0.0, {})

    # Split into reference and current
    dates = data.index.sort_values()
    total_months = config.reference_months + config.current_months

    if len(dates) < total_months:
        split_idx = int(len(data) * 0.7)
        reference = data.iloc[:split_idx]
        current = data.iloc[split_idx:]
    else:
        cutoff = dates[-config.current_months]
        ref_start = dates[-(config.reference_months + config.current_months)]
        reference = data.loc[ref_start:cutoff].iloc[:-1]
        current = data.loc[cutoff:]

    # Filter to columns with enough data
    valid_cols = [
        c for c in data.columns
        if reference[c].notna().sum() > 3 and current[c].notna().sum() > 1
    ]

    if not valid_cols:
        return DriftResult(False, 0, 0, 0.0, {})

    # Run KS-test on each feature
    n_total = len(valid_cols)
    n_drifted = 0
    feature_details = {}

    for col in valid_cols:
        ref_vals = reference[col].dropna().values
        cur_vals = current[col].dropna().values

        if len(ref_vals) < 3 or len(cur_vals) < 1:
            continue

        # Kolmogorov-Smirnov test (distribution shift)
        ks_stat, ks_p = stats.ks_2samp(ref_vals, cur_vals)

        # Welch's t-test (mean shift)
        if len(cur_vals) >= 2:
            t_stat, t_p = stats.ttest_ind(ref_vals, cur_vals, equal_var=False)
        else:
            t_stat, t_p = 0.0, 1.0

        # Drift detected if either test is significant
        drifted = ks_p < config.p_value_threshold or t_p < config.p_value_threshold

        # Drift score: combine both (lower p-value = higher drift score)
        drift_score = 1.0 - min(ks_p, t_p)

        if drifted:
            n_drifted += 1

        # Compute summary stats for context
        ref_mean = float(np.nanmean(ref_vals))
        cur_mean = float(np.nanmean(cur_vals))
        ref_std = float(np.nanstd(ref_vals)) if len(ref_vals) > 1 else 0.0

        feature_details[col] = {
            "drifted": drifted,
            "drift_score": round(drift_score, 4),
            "ks_statistic": round(ks_stat, 4),
            "ks_p_value": round(ks_p, 4),
            "t_p_value": round(t_p, 4),
            "stattest": "KS + Welch-t",
            "threshold": config.p_value_threshold,
            "ref_mean": round(ref_mean, 4),
            "cur_mean": round(cur_mean, 4),
            "shift_magnitude": round(
                (cur_mean - ref_mean) / ref_std if ref_std > 0 else 0.0, 2
            ),
        }

    drift_share = n_drifted / n_total if n_total > 0 else 0.0
    dataset_drift = drift_share > 0.25  # 25%+ features drifted = dataset drift

    return DriftResult(
        dataset_drift=dataset_drift,
        n_drifted_features=n_drifted,
        n_total_features=n_total,
        drift_share=drift_share,
        feature_details=feature_details,
        report_path=None,
    )


def compute_prediction_drift(
    regime_probs_reference: pd.DataFrame,
    regime_probs_current: pd.DataFrame,
    output_path: str | Path | None = None,
) -> DriftResult:
    """Run drift analysis on regime probability predictions."""
    from scipy import stats

    if regime_probs_reference.empty or regime_probs_current.empty:
        return DriftResult(False, 0, 0, 0.0, {})

    n_total = len(regime_probs_reference.columns)
    n_drifted = 0
    feature_details = {}

    for col in regime_probs_reference.columns:
        if col not in regime_probs_current.columns:
            continue
        ref_vals = regime_probs_reference[col].dropna().values
        cur_vals = regime_probs_current[col].dropna().values
        if len(ref_vals) < 3 or len(cur_vals) < 1:
            continue

        ks_stat, ks_p = stats.ks_2samp(ref_vals, cur_vals)
        drifted = ks_p < 0.05
        if drifted:
            n_drifted += 1
        feature_details[col] = {
            "drifted": drifted,
            "drift_score": round(1.0 - ks_p, 4),
        }

    drift_share = n_drifted / n_total if n_total > 0 else 0.0

    return DriftResult(
        dataset_drift=drift_share > 0.25,
        n_drifted_features=n_drifted,
        n_total_features=n_total,
        drift_share=drift_share,
        feature_details=feature_details,
        report_path=None,
    )
