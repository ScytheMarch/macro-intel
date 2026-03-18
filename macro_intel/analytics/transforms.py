"""Time series transforms for economic indicator analysis.

Adapted from econ-monitor with panel-level extensions.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def mom_change(s: pd.Series) -> pd.Series:
    """Month-over-month absolute change."""
    return s.diff()


def mom_pct(s: pd.Series) -> pd.Series:
    """Month-over-month percent change."""
    return s.pct_change() * 100


def yoy_pct(s: pd.Series, periods: int = 12) -> pd.Series:
    """Year-over-year percent change."""
    return s.pct_change(periods=periods) * 100


def qoq_pct(s: pd.Series) -> pd.Series:
    """Quarter-over-quarter percent change."""
    return s.pct_change() * 100


def annualized_qoq(s: pd.Series) -> pd.Series:
    """Annualized quarter-over-quarter growth rate."""
    qoq = s.pct_change()
    return ((1 + qoq) ** 4 - 1) * 100


def moving_average(s: pd.Series, window: int) -> pd.Series:
    """Simple moving average."""
    return s.rolling(window=window, min_periods=1).mean()


def rate_of_change(s: pd.Series, periods: int = 1) -> pd.Series:
    """Rate of change over N periods."""
    return s.pct_change(periods=periods) * 100


def z_score(s: pd.Series, lookback: int = 60) -> pd.Series:
    """Rolling z-score: how many std devs from rolling mean."""
    roll_mean = s.rolling(window=lookback, min_periods=max(lookback // 2, 2)).mean()
    roll_std = s.rolling(window=lookback, min_periods=max(lookback // 2, 2)).std()
    return (s - roll_mean) / roll_std.replace(0, np.nan)


def latest_z_score(s: pd.Series, lookback: int = 60) -> float | None:
    """Z-score of the most recent observation."""
    zs = z_score(s, lookback).dropna()
    if zs.empty:
        return None
    return float(zs.iloc[-1])


def trend_direction(s: pd.Series, window: int = 6) -> str:
    """Classify recent trend as 'improving', 'stable', or 'deteriorating'."""
    recent = s.dropna().tail(window)
    if len(recent) < 3:
        return "stable"

    x = np.arange(len(recent), dtype=float)
    y = recent.values.astype(float)
    y_range = y.max() - y.min()
    if y_range == 0:
        return "stable"

    slope = np.polyfit(x, y, 1)[0]
    normalized_slope = slope / y_range * len(recent)

    if normalized_slope > 0.15:
        return "improving"
    elif normalized_slope < -0.15:
        return "deteriorating"
    return "stable"


def apply_transform(s: pd.Series, transform: str, frequency: str = "monthly") -> pd.Series:
    """Apply indicator's configured transform to raw data."""
    if transform == "yoy_pct":
        periods = {"daily": 252, "weekly": 52, "monthly": 12, "quarterly": 4}.get(frequency, 12)
        return yoy_pct(s, periods=periods)
    elif transform == "mom_pct":
        return mom_pct(s)
    elif transform == "net_change":
        return mom_change(s)
    elif transform == "annualized":
        return annualized_qoq(s)
    return s  # "level"


def compute_summary(s: pd.Series) -> dict:
    """Summary statistics for a series."""
    clean = s.dropna()
    if clean.empty:
        return {}
    return {
        "latest": float(clean.iloc[-1]),
        "previous": float(clean.iloc[-2]) if len(clean) >= 2 else None,
        "change": float(clean.iloc[-1] - clean.iloc[-2]) if len(clean) >= 2 else None,
        "min_1y": float(clean.tail(12).min()),
        "max_1y": float(clean.tail(12).max()),
        "mean_1y": float(clean.tail(12).mean()),
        "std_1y": float(clean.tail(12).std()) if len(clean.tail(12)) > 1 else 0,
        "count": len(clean),
    }
