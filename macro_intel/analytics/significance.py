"""Significance analysis for recent economic data changes.

Computes how meaningful a new reading is relative to historical context.
Adapted from econ-monitor.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from macro_intel.analytics.transforms import apply_transform, latest_z_score


def compute_significance(
    raw_series: pd.Series,
    transform: str,
    frequency: str,
    higher_is: str,
) -> dict:
    """Compute full significance analysis for the latest data point.

    Returns dict with magnitude, z_score, percentile, streak, interpretation.
    """
    transformed = apply_transform(raw_series, transform, frequency)
    clean = transformed.dropna()

    if len(clean) < 6:
        return _empty_result()

    latest = float(clean.iloc[-1])
    prev = float(clean.iloc[-2])

    # Z-score
    z = latest_z_score(clean, lookback=60) or 0.0

    # Percentile rank
    lookback = clean.tail(60)
    percentile = float((lookback < latest).sum() / len(lookback) * 100)

    # Versus moving averages
    def _vs_avg(window: int) -> float | None:
        if len(clean) < window:
            return None
        avg = float(clean.tail(window).mean())
        if avg == 0:
            return 0.0
        return round((latest - avg) / abs(avg) * 100, 2)

    vs_3m = _vs_avg(3)
    vs_6m = _vs_avg(6)
    vs_12m = _vs_avg(12)

    # Streak
    diffs = clean.diff().dropna().tail(12)
    streak = 0
    if len(diffs) > 0:
        last_sign = 1 if diffs.iloc[-1] > 0 else -1
        for val in reversed(diffs.values):
            if (val > 0 and last_sign > 0) or (val < 0 and last_sign < 0):
                streak += last_sign
            else:
                break

    # Magnitude classification
    abs_z = abs(z)
    if abs_z < 0.5:
        magnitude, magnitude_color = "small", "#6b7280"
    elif abs_z < 1.0:
        magnitude, magnitude_color = "moderate", "#eab308"
    elif abs_z < 2.0:
        magnitude, magnitude_color = "large", "#f97316"
    else:
        magnitude, magnitude_color = "extreme", "#ef4444"

    # Interpretation
    change = latest - prev
    change_dir = "rose" if change > 0 else "fell" if change < 0 else "was unchanged"

    signal_map = {
        "inflationary": ("hotter inflation pressure", "cooling inflation", "stable inflation"),
        "expansionary": ("strengthening activity", "weakening activity", "steady activity"),
        "contractionary": ("increasing stress", "easing stress", "stable conditions"),
    }
    signals = signal_map.get(higher_is, ("neutral shift", "neutral shift", "neutral"))
    econ_signal = signals[0] if change > 0 else signals[1] if change < 0 else signals[2]

    streak_text = ""
    if abs(streak) >= 3:
        streak_dir = "increases" if streak > 0 else "decreases"
        streak_text = f" This marks {abs(streak)} consecutive {streak_dir}."

    pctl_text = (
        f"at the {percentile:.0f}th percentile (near highs)" if percentile >= 90
        else f"at the {percentile:.0f}th percentile (near lows)" if percentile <= 10
        else f"at the {percentile:.0f}th percentile"
    )

    interpretation = (
        f"The latest reading {change_dir} by {abs(change):.2f}, signaling {econ_signal}. "
        f"This is a **{magnitude}** move ({z:+.1f}\u03c3), {pctl_text} of recent history."
        f"{streak_text}"
    )

    return {
        "magnitude": magnitude,
        "magnitude_color": magnitude_color,
        "z_score": round(z, 2),
        "percentile": round(percentile, 1),
        "vs_3m_avg": vs_3m,
        "vs_6m_avg": vs_6m,
        "vs_12m_avg": vs_12m,
        "streak": streak,
        "latest": latest,
        "previous": prev,
        "change": round(change, 4),
        "interpretation": interpretation,
    }


def _empty_result() -> dict:
    return {
        "magnitude": "unknown",
        "magnitude_color": "#6b7280",
        "z_score": 0,
        "percentile": 50,
        "vs_3m_avg": None,
        "vs_6m_avg": None,
        "vs_12m_avg": None,
        "streak": 0,
        "latest": None,
        "previous": None,
        "change": None,
        "interpretation": "Insufficient data for significance analysis.",
    }
