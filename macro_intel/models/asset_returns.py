"""Regime-conditional asset return distributions.

Maps regime posteriors to expected return distributions for portfolio context.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from macro_intel.models.regime_hmm import RegimeResult

logger = logging.getLogger(__name__)


@dataclass
class RegimeReturnProfile:
    """Expected return distribution conditioned on each regime."""
    regime_label: str
    mean_return: float          # Annualized mean return
    volatility: float           # Annualized volatility
    sharpe: float               # Risk-adjusted return
    prob_negative: float        # Probability of negative annual return
    hdi_90: tuple[float, float] # 90% highest density interval


def compute_regime_returns(
    result: RegimeResult,
    equity_returns: pd.Series,
    risk_free_rate: float = 0.04,
) -> list[RegimeReturnProfile]:
    """Compute return profiles conditioned on each regime.

    Args:
        result: Output from regime model fitting
        equity_returns: Monthly equity returns (as fractions, e.g., 0.02 = 2%)
        risk_free_rate: Annual risk-free rate

    Returns:
        List of RegimeReturnProfile, one per regime.
    """
    K = result.regime_probs.shape[1]
    regime_map = result.regime_map

    # Align returns to model dates
    if hasattr(equity_returns.index, 'tz') and equity_returns.index.tz is not None:
        equity_returns.index = equity_returns.index.tz_localize(None)

    aligned = equity_returns.reindex(result.dates).dropna()
    if len(aligned) < 12:
        logger.warning("Insufficient return data for regime conditioning")
        return []

    # Match regime states to returns
    regime_states = regime_map[:len(aligned)]

    profiles = []
    for k in range(K):
        mask = regime_states == k
        regime_returns = aligned.values[mask]

        if len(regime_returns) < 6:
            # Insufficient data: use unconditional
            regime_returns = aligned.values

        # Annualize
        monthly_mean = float(np.mean(regime_returns))
        monthly_std = float(np.std(regime_returns, ddof=1)) if len(regime_returns) > 1 else 0.0
        annual_mean = (1 + monthly_mean) ** 12 - 1
        annual_vol = monthly_std * np.sqrt(12)

        # Sharpe
        excess = annual_mean - risk_free_rate
        sharpe = excess / annual_vol if annual_vol > 0 else 0.0

        # Probability of negative return (assuming normal, simplified)
        from scipy.stats import norm
        prob_neg = float(norm.cdf(0, loc=annual_mean, scale=annual_vol)) if annual_vol > 0 else 0.0

        # HDI approximation
        hdi_lo = annual_mean - 1.645 * annual_vol
        hdi_hi = annual_mean + 1.645 * annual_vol

        label = result.regime_labels[k] if k < len(result.regime_labels) else f"Regime_{k}"

        profiles.append(RegimeReturnProfile(
            regime_label=label,
            mean_return=round(annual_mean, 4),
            volatility=round(annual_vol, 4),
            sharpe=round(sharpe, 2),
            prob_negative=round(prob_neg, 3),
            hdi_90=(round(hdi_lo, 4), round(hdi_hi, 4)),
        ))

    return profiles


def current_regime_forecast(
    result: RegimeResult,
    return_profiles: list[RegimeReturnProfile],
) -> dict:
    """Compute probability-weighted expected return using current regime posteriors.

    Returns:
        Dict with weighted expected return, volatility, and regime breakdown.
    """
    if not return_profiles:
        return {"expected_return": None, "expected_vol": None, "breakdown": []}

    # Use last time step's regime probabilities
    current_probs = result.regime_probs[-1]  # (K,)
    K = len(current_probs)

    weighted_return = 0.0
    weighted_vol_sq = 0.0
    breakdown = []

    for k in range(min(K, len(return_profiles))):
        p = float(current_probs[k])
        r = return_profiles[k].mean_return
        v = return_profiles[k].volatility

        weighted_return += p * r
        weighted_vol_sq += p * (v ** 2 + r ** 2)

        breakdown.append({
            "regime": return_profiles[k].regime_label,
            "probability": round(p, 3),
            "expected_return": round(r, 4),
            "volatility": round(v, 4),
            "contribution": round(p * r, 4),
        })

    weighted_vol = float(np.sqrt(weighted_vol_sq - weighted_return ** 2))

    return {
        "expected_return": round(weighted_return, 4),
        "expected_volatility": round(weighted_vol, 4),
        "uncertainty": round(result.uncertainty, 3),
        "breakdown": sorted(breakdown, key=lambda x: x["probability"], reverse=True),
    }
