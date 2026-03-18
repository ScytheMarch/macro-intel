"""Feature panel assembler: builds the unified Date x Country x Feature matrix.

Combines FRED macro data, World Bank structural data, and market returns
into a single MultiIndex DataFrame for model consumption.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from macro_intel.config.countries import COUNTRIES, G7_COUNTRIES
from macro_intel.config.indicators import INDICATORS, get_fred_indicators, get_wb_indicators
from macro_intel.data import cache

logger = logging.getLogger(__name__)


@dataclass
class PanelConfig:
    """Configuration for feature panel assembly."""
    countries: list[str] = field(default_factory=lambda: ["USA"])
    fred_indicators: list[str] | None = None   # None = all FRED indicators
    wb_indicators: list[str] | None = None      # None = all WB indicators
    include_market_returns: bool = True
    start_date: str = "2000-01-01"
    frequency: str = "M"  # Monthly


def build_panel(config: PanelConfig | None = None) -> pd.DataFrame:
    """Assemble the full feature panel from cached data.

    Returns DataFrame with MultiIndex (date, country) and feature columns.

    Must call the data fetch functions first to populate the cache.
    """
    if config is None:
        config = PanelConfig()

    frames_by_country: dict[str, pd.DataFrame] = {}

    for country in config.countries:
        country_frames: dict[str, pd.Series] = {}

        # ── FRED data (US-only for now, extensible) ──────────────────────
        if country == "USA":
            fred_ids = config.fred_indicators
            if fred_ids is None:
                fred_ids = list(get_fred_indicators().keys())

            for sid in fred_ids:
                df = cache.get_observations(sid, country="USA", start_date=config.start_date)
                if not df.empty:
                    # Resample to monthly (take last value of each month)
                    monthly = df["value"].resample("ME").last().dropna()
                    country_frames[sid] = monthly

        # ── World Bank data (all countries) ──────────────────────────────
        wb_ids = config.wb_indicators
        if wb_ids is None:
            wb_ids = list(get_wb_indicators().keys())

        for sid in wb_ids:
            df = cache.get_observations(sid, country=country, start_date=config.start_date)
            if not df.empty:
                # WB data is annual — resample to monthly with forward fill
                monthly = df["value"].resample("ME").last().ffill()
                country_frames[sid] = monthly

        # ── Market index returns ─────────────────────────────────────────
        if config.include_market_returns:
            market_sid = f"MKT_{country}"
            df = cache.get_observations(market_sid, country=country, start_date=config.start_date)
            if not df.empty:
                monthly = df["value"].resample("ME").last().dropna()
                returns = monthly.pct_change() * 100  # As percentage
                country_frames["EQUITY_RETURN"] = returns

        # ── Combine into country DataFrame ───────────────────────────────
        if country_frames:
            country_df = pd.DataFrame(country_frames)
            country_df["country"] = country
            frames_by_country[country] = country_df

    if not frames_by_country:
        logger.warning("No data available for panel assembly")
        return pd.DataFrame()

    # Concatenate all countries
    panel = pd.concat(frames_by_country.values(), axis=0)

    # Set MultiIndex (date, country)
    panel.index.name = "date"
    panel = panel.reset_index()
    panel = panel.set_index(["date", "country"])
    panel = panel.sort_index()

    # Drop rows where all feature columns are NaN
    feature_cols = [c for c in panel.columns]
    panel = panel.dropna(how="all", subset=feature_cols)

    return panel


def align_frequencies(panel: pd.DataFrame, freq: str = "M") -> pd.DataFrame:
    """Resample panel to common frequency, forward-filling gaps.

    Operates per-country group.
    """
    if panel.empty:
        return panel

    aligned_parts = []
    for country in panel.index.get_level_values("country").unique():
        country_data = panel.xs(country, level="country")
        resampled = country_data.resample(freq).last().ffill()
        resampled["country"] = country
        resampled = resampled.reset_index()
        resampled = resampled.set_index(["date", "country"])
        aligned_parts.append(resampled)

    return pd.concat(aligned_parts).sort_index()


def standardize_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Z-score standardize all features within each country (for model input).

    Returns a copy with standardized values.
    """
    if panel.empty:
        return panel

    result = panel.copy()
    feature_cols = [c for c in result.columns if c != "country"]

    for country in result.index.get_level_values("country").unique():
        mask = result.index.get_level_values("country") == country
        country_data = result.loc[mask, feature_cols]
        means = country_data.mean()
        stds = country_data.std().replace(0, np.nan)
        result.loc[mask, feature_cols] = (country_data - means) / stds

    return result


def get_panel_summary(panel: pd.DataFrame) -> dict:
    """Summary statistics for the feature panel."""
    if panel.empty:
        return {"n_rows": 0, "n_features": 0, "countries": [], "date_range": None}

    countries = list(panel.index.get_level_values("country").unique())
    dates = panel.index.get_level_values("date")

    return {
        "n_rows": len(panel),
        "n_features": len(panel.columns),
        "features": list(panel.columns),
        "countries": countries,
        "date_range": (str(dates.min().date()), str(dates.max().date())),
        "missing_pct": float(panel.isna().mean().mean() * 100),
        "obs_per_country": {
            c: int((panel.index.get_level_values("country") == c).sum())
            for c in countries
        },
    }
