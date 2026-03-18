"""Historical analog finder.

Identifies past periods most similar to the current macro environment
based on regime posteriors and feature panel values.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from macro_intel.models.regime_hmm import RegimeResult

logger = logging.getLogger(__name__)


@dataclass
class AnalogPeriod:
    """A historical period similar to the current environment."""
    start_date: str
    end_date: str
    similarity_score: float     # 0-1, higher = more similar
    regime_label: str
    duration_months: int
    # What happened next (forward-looking from the analog period)
    forward_return_6m: float | None = None
    forward_return_12m: float | None = None
    description: str = ""


def find_analogs(
    regime_result: RegimeResult,
    panel: pd.DataFrame,
    country: str = "USA",
    n_analogs: int = 5,
    lookback_window: int = 6,
    equity_returns: pd.Series | None = None,
) -> list[AnalogPeriod]:
    """Find historical periods most similar to the current macro state.

    Uses a combination of:
    1. Regime posterior similarity (Jensen-Shannon divergence)
    2. Feature value similarity (Euclidean distance in z-scored space)

    Args:
        regime_result: Fitted regime model output
        panel: Feature panel with MultiIndex (date, country)
        country: Country to analyze
        n_analogs: Number of analog periods to return
        lookback_window: Months of context for comparison
        equity_returns: Optional monthly returns for forward-looking analysis
    """
    probs = regime_result.regime_probs  # (T, K)
    dates = regime_result.dates
    T = len(dates)

    if T < lookback_window + 12:
        logger.warning("Insufficient history for analog search")
        return []

    # Current window: last `lookback_window` time steps
    current_probs = probs[-lookback_window:]  # (W, K)
    current_mean_probs = current_probs.mean(axis=0)

    # Get feature data for distance computation
    try:
        features = panel.xs(country, level="country")
        feature_cols = [c for c in features.columns if features[c].dtype in [np.float64, float]]
        features_aligned = features.reindex(dates)[feature_cols].fillna(method="ffill")
    except Exception:
        features_aligned = pd.DataFrame()

    # Score each historical window
    candidates: list[tuple[int, float]] = []
    min_start = 0
    max_start = T - lookback_window - 12  # Leave room for forward-looking

    for t in range(min_start, max_start):
        window_probs = probs[t:t + lookback_window]
        window_mean = window_probs.mean(axis=0)

        # 1. Regime similarity (1 - JSD)
        from scipy.spatial.distance import jensenshannon
        jsd = jensenshannon(current_mean_probs, window_mean)
        regime_sim = 1.0 - jsd if not np.isnan(jsd) else 0.0

        # 2. Feature similarity (normalized euclidean)
        feature_sim = 0.5  # Default if no features
        if not features_aligned.empty and len(features_aligned) > t + lookback_window:
            current_feat = features_aligned.iloc[-lookback_window:].mean()
            window_feat = features_aligned.iloc[t:t + lookback_window].mean()
            common = current_feat.dropna().index.intersection(window_feat.dropna().index)
            if len(common) > 3:
                diff = current_feat[common] - window_feat[common]
                dist = float(np.sqrt((diff ** 2).sum()))
                feature_sim = 1.0 / (1.0 + dist / len(common))

        # Combined score (weighted)
        score = 0.6 * regime_sim + 0.4 * feature_sim
        candidates.append((t, score))

    # Sort by score, take top N (with minimum separation of lookback_window months)
    candidates.sort(key=lambda x: x[1], reverse=True)

    selected: list[AnalogPeriod] = []
    used_windows: list[int] = []

    for t, score in candidates:
        # Ensure no overlap with already selected
        if any(abs(t - u) < lookback_window for u in used_windows):
            continue

        start = dates[t]
        end = dates[t + lookback_window - 1]
        regime_idx = int(np.argmax(probs[t:t + lookback_window].mean(axis=0)))
        regime_label = regime_result.regime_labels[regime_idx]

        # Forward returns
        fwd_6m = None
        fwd_12m = None
        if equity_returns is not None:
            try:
                end_idx = t + lookback_window
                if end_idx + 6 <= T:
                    fwd_dates_6 = dates[end_idx:end_idx + 6]
                    fwd_ret = equity_returns.reindex(fwd_dates_6).dropna()
                    if len(fwd_ret) > 0:
                        fwd_6m = float((1 + fwd_ret).prod() - 1)
                if end_idx + 12 <= T:
                    fwd_dates_12 = dates[end_idx:end_idx + 12]
                    fwd_ret = equity_returns.reindex(fwd_dates_12).dropna()
                    if len(fwd_ret) > 0:
                        fwd_12m = float((1 + fwd_ret).prod() - 1)
            except Exception:
                pass

        selected.append(AnalogPeriod(
            start_date=str(start.date()),
            end_date=str(end.date()),
            similarity_score=round(score, 3),
            regime_label=regime_label,
            duration_months=lookback_window,
            forward_return_6m=round(fwd_6m, 4) if fwd_6m is not None else None,
            forward_return_12m=round(fwd_12m, 4) if fwd_12m is not None else None,
        ))

        used_windows.append(t)
        if len(selected) >= n_analogs:
            break

    return selected
