"""Market data client for equity indices and asset prices.

Uses yfinance for price data, keyed by country market index.
"""

from __future__ import annotations

import logging

import pandas as pd

from macro_intel.config.countries import COUNTRIES

logger = logging.getLogger(__name__)


def fetch_index_prices(
    country: str,
    period: str = "10y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Fetch daily prices for a country's primary equity index.

    Returns DataFrame with DatetimeIndex and 'value' column (close prices).
    """
    import yfinance as yf

    c = COUNTRIES.get(country)
    if c is None:
        logger.warning("Unknown country: %s", country)
        return pd.DataFrame(columns=["value"])

    try:
        ticker = c.market_index
        hist = yf.download(ticker, period=period, interval=interval, progress=False)

        if hist.empty:
            return pd.DataFrame(columns=["value"])

        # Handle MultiIndex columns from newer yfinance
        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = hist.columns.get_level_values(0)

        if "Close" in hist.columns:
            df = hist[["Close"]].rename(columns={"Close": "value"}).dropna()
        elif "Adj Close" in hist.columns:
            df = hist[["Adj Close"]].rename(columns={"Adj Close": "value"}).dropna()
        else:
            return pd.DataFrame(columns=["value"])

        df.index = pd.to_datetime(df.index)
        df.index = df.index.tz_localize(None)  # Strip timezone
        return df

    except Exception as e:
        logger.error("Failed to fetch index for %s (%s): %s", country, c.market_index, e)
        return pd.DataFrame(columns=["value"])


def fetch_multiple_indices(
    countries: list[str],
    period: str = "10y",
) -> dict[str, pd.DataFrame]:
    """Fetch index prices for multiple countries."""
    results = {}
    for country in countries:
        results[country] = fetch_index_prices(country, period)
    return results


def compute_returns(prices: pd.DataFrame, period: str = "M") -> pd.DataFrame:
    """Compute periodic returns from daily prices.

    Args:
        prices: DataFrame with 'value' column and DatetimeIndex
        period: Resample period ('M' for monthly, 'W' for weekly)

    Returns:
        DataFrame with 'value' column containing periodic returns (as fractions).
    """
    if prices.empty:
        return pd.DataFrame(columns=["value"])

    resampled = prices["value"].resample(period).last().dropna()
    returns = resampled.pct_change().dropna()
    return returns.to_frame("value")
