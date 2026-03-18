"""World Bank Indicators API client using wbgapi.

Fetches cross-country structural data (annual frequency) for macro analysis.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def _get_wbgapi():
    """Lazy import of wbgapi."""
    try:
        import wbgapi as wb
        return wb
    except ImportError:
        logger.error("wbgapi not installed. Run: pip install wbgapi")
        return None


def fetch_indicator(
    indicator: str,
    countries: list[str] | str = "all",
    start_year: int = 2000,
    end_year: int | None = None,
) -> pd.DataFrame:
    """Fetch a World Bank indicator for specified countries.

    Returns DataFrame with columns: ['country', 'date', 'value']
    where date is the year as a datetime (Jan 1).
    """
    wb = _get_wbgapi()
    if wb is None:
        return pd.DataFrame(columns=["country", "date", "value"])

    try:
        # wbgapi.data.DataFrame returns countries as rows, years as columns
        if end_year is None:
            from datetime import datetime
            end_year = datetime.now().year - 1

        time_range = range(start_year, end_year + 1)

        df = wb.data.DataFrame(
            indicator,
            economy=countries if countries != "all" else None,
            time=time_range,
            labels=False,
            numericTimeKeys=True,
            columns="time",
        )

        if df.empty:
            logger.warning("No data from World Bank for %s", indicator)
            return pd.DataFrame(columns=["country", "date", "value"])

        # df: index = country codes, columns = year ints, values = indicator values
        records = []
        for country_code in df.index:
            for year in df.columns:
                val = df.loc[country_code, year]
                if pd.notna(val):
                    records.append({
                        "country": str(country_code),
                        "date": pd.Timestamp(year=int(year), month=1, day=1),
                        "value": float(val),
                    })

        result = pd.DataFrame(records)
        if result.empty:
            return pd.DataFrame(columns=["country", "date", "value"])

        return result.sort_values(["country", "date"]).reset_index(drop=True)

    except Exception as e:
        logger.error("World Bank fetch failed for %s: %s", indicator, e)
        return pd.DataFrame(columns=["country", "date", "value"])


def fetch_multiple_indicators(
    indicators: list[str],
    countries: list[str] | str = "all",
    start_year: int = 2000,
    end_year: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Fetch multiple World Bank indicators.

    Returns dict mapping indicator_code -> DataFrame.
    """
    results = {}
    for ind_code in indicators:
        results[ind_code] = fetch_indicator(
            ind_code, countries, start_year, end_year,
        )
    return results


def search_indicators(query: str, max_results: int = 20) -> list[dict]:
    """Search World Bank indicators by keyword."""
    wb = _get_wbgapi()
    if wb is None:
        return []

    try:
        results = []
        for row in wb.series.info(q=query):
            results.append({
                "id": row["id"],
                "value": row.get("value", ""),
            })
            if len(results) >= max_results:
                break
        return results
    except Exception as e:
        logger.error("WB search failed: %s", e)
        return []


def get_available_countries() -> list[dict]:
    """List available countries in the World Bank database."""
    wb = _get_wbgapi()
    if wb is None:
        return []

    try:
        countries = []
        for c in wb.economy.info():
            countries.append({
                "id": c["id"],
                "value": c.get("value", ""),
            })
        return countries
    except Exception as e:
        logger.error("WB country list failed: %s", e)
        return []
