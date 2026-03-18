"""Cross-indicator and cross-country correlation analysis."""

from __future__ import annotations

import pandas as pd
import numpy as np

from macro_intel.data import cache
from macro_intel.config.indicators import get_fred_indicators


def build_indicator_correlation_matrix(
    series_ids: list[str] | None = None,
    country: str = "USA",
    lookback_months: int = 36,
) -> pd.DataFrame:
    """Build correlation matrix of month-over-month changes across indicators."""
    if series_ids is None:
        series_ids = [
            sid for sid, ind in get_fred_indicators().items()
            if ind.frequency in ("monthly", "quarterly")
        ]

    frames = {}
    for sid in series_ids:
        df = cache.get_observations(sid, country=country)
        if df.empty or len(df) < 6:
            continue
        monthly = df["value"].resample("ME").last().dropna()
        pct = monthly.pct_change().dropna()
        if len(pct) >= 6:
            frames[sid] = pct.tail(lookback_months)

    if len(frames) < 2:
        return pd.DataFrame()

    combined = pd.DataFrame(frames)
    return combined.corr()


def build_cross_country_correlation(
    series_id: str,
    countries: list[str],
    lookback_months: int = 60,
    rolling_window: int = 12,
) -> pd.DataFrame:
    """Build rolling correlation matrix for a single indicator across countries.

    Returns a DataFrame where rows=date, columns=country pairs,
    values=rolling correlation.
    """
    frames = {}
    for country in countries:
        df = cache.get_observations(series_id, country=country)
        if df.empty:
            continue
        monthly = df["value"].resample("ME").last().dropna()
        pct = monthly.pct_change().dropna()
        if len(pct) >= rolling_window:
            frames[country] = pct.tail(lookback_months)

    if len(frames) < 2:
        return pd.DataFrame()

    combined = pd.DataFrame(frames)

    # Compute rolling pairwise correlations
    pairs = {}
    countries_list = list(combined.columns)
    for i, c1 in enumerate(countries_list):
        for c2 in countries_list[i + 1:]:
            pair_key = f"{c1}-{c2}"
            pairs[pair_key] = combined[c1].rolling(rolling_window).corr(combined[c2])

    return pd.DataFrame(pairs).dropna(how="all")


def compute_similarity_matrix(
    panel: pd.DataFrame,
    method: str = "correlation",
) -> pd.DataFrame:
    """Compute country-to-country similarity from a feature panel.

    Args:
        panel: MultiIndex (date, country) DataFrame
        method: "correlation" or "euclidean"

    Returns:
        Square DataFrame of country-to-country similarity scores.
    """
    countries = list(panel.index.get_level_values("country").unique())

    if method == "correlation":
        # Average cross-feature correlation between country time series
        sim = pd.DataFrame(1.0, index=countries, columns=countries)
        for i, c1 in enumerate(countries):
            d1 = panel.xs(c1, level="country").dropna(axis=1, how="all")
            for c2 in countries[i + 1:]:
                d2 = panel.xs(c2, level="country").dropna(axis=1, how="all")
                common = list(set(d1.columns) & set(d2.columns))
                if len(common) < 3:
                    sim.loc[c1, c2] = sim.loc[c2, c1] = 0.0
                    continue
                # Align dates
                merged = pd.merge(
                    d1[common], d2[common],
                    left_index=True, right_index=True,
                    suffixes=("_1", "_2"),
                )
                if len(merged) < 6:
                    sim.loc[c1, c2] = sim.loc[c2, c1] = 0.0
                    continue
                # Mean correlation across features
                corrs = []
                for col in common:
                    c = merged[f"{col}_1"].corr(merged[f"{col}_2"])
                    if pd.notna(c):
                        corrs.append(c)
                avg_corr = float(np.mean(corrs)) if corrs else 0.0
                sim.loc[c1, c2] = sim.loc[c2, c1] = avg_corr
        return sim

    else:  # euclidean distance inverted to similarity
        sim = pd.DataFrame(0.0, index=countries, columns=countries)
        for i, c1 in enumerate(countries):
            d1 = panel.xs(c1, level="country").mean()
            sim.loc[c1, c1] = 1.0
            for c2 in countries[i + 1:]:
                d2 = panel.xs(c2, level="country").mean()
                common = d1.dropna().index.intersection(d2.dropna().index)
                if len(common) == 0:
                    continue
                dist = float(np.sqrt(((d1[common] - d2[common]) ** 2).sum()))
                similarity = 1.0 / (1.0 + dist)
                sim.loc[c1, c2] = sim.loc[c2, c1] = similarity
        return sim


def find_divergences(
    country: str = "USA",
    threshold: float = 0.6,
    lookback_months: int = 12,
) -> list[dict]:
    """Find indicator pairs historically correlated but currently diverging."""
    long_term = build_indicator_correlation_matrix(country=country, lookback_months=60)
    short_term = build_indicator_correlation_matrix(country=country, lookback_months=lookback_months)

    if long_term.empty or short_term.empty:
        return []

    common = list(set(long_term.columns) & set(short_term.columns))
    divergences = []

    for i, s1 in enumerate(common):
        for s2 in common[i + 1:]:
            hist = long_term.loc[s1, s2]
            recent = short_term.loc[s1, s2] if s2 in short_term.columns else hist
            if abs(hist) > threshold and abs(hist - recent) > 0.4:
                divergences.append({
                    "pair": (s1, s2),
                    "historical_corr": round(hist, 3),
                    "recent_corr": round(recent, 3),
                })

    return sorted(divergences, key=lambda d: abs(d["historical_corr"] - d["recent_corr"]), reverse=True)
