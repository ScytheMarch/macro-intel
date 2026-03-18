"""Map portfolio holdings to country, sector, and factor exposures.

Uses yfinance metadata to resolve ticker -> country/sector mappings.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Common ETF -> country mappings
_ETF_COUNTRY_MAP: dict[str, str] = {
    "SPY": "USA", "VOO": "USA", "VTI": "USA", "QQQ": "USA", "IWM": "USA",
    "EFA": "INTL", "VXUS": "INTL", "VEA": "INTL",
    "EEM": "EM", "VWO": "EM", "IEMG": "EM",
    "EWJ": "JPN", "EWG": "DEU", "EWU": "GBR", "EWC": "CAN",
    "FXI": "CHN", "EWZ": "BRA", "EWY": "KOR", "EWA": "AUS",
    "INDA": "IND", "EWI": "ITA", "EWQ": "FRA",
    "BND": "USA", "AGG": "USA", "TLT": "USA", "SHY": "USA",
    "GLD": "GLOBAL", "SLV": "GLOBAL", "USO": "GLOBAL",
}

# Common ETF -> sector mappings
_ETF_SECTOR_MAP: dict[str, str] = {
    "XLK": "Technology", "XLF": "Financials", "XLV": "Healthcare",
    "XLE": "Energy", "XLI": "Industrials", "XLP": "Consumer Staples",
    "XLY": "Consumer Discretionary", "XLU": "Utilities", "XLRE": "Real Estate",
    "XLC": "Communication", "XLB": "Materials",
    "VNQ": "Real Estate", "VGT": "Technology", "VHT": "Healthcare",
    "BND": "Fixed Income", "AGG": "Fixed Income", "TLT": "Fixed Income",
    "GLD": "Commodities", "SLV": "Commodities", "USO": "Commodities",
}


def resolve_country(ticker: str) -> str:
    """Resolve a ticker to its primary country exposure."""
    if ticker in _ETF_COUNTRY_MAP:
        return _ETF_COUNTRY_MAP[ticker]

    # Try yfinance
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        country = info.get("country", "")
        if country:
            # Map common country names to ISO3
            country_map = {
                "United States": "USA", "United Kingdom": "GBR",
                "Germany": "DEU", "Japan": "JPN", "Canada": "CAN",
                "France": "FRA", "Italy": "ITA", "China": "CHN",
                "India": "IND", "Brazil": "BRA", "South Korea": "KOR",
                "Australia": "AUS",
            }
            return country_map.get(country, country[:3].upper())
    except Exception:
        pass

    return "USA"  # Default assumption


def resolve_sector(ticker: str) -> str:
    """Resolve a ticker to its sector."""
    if ticker in _ETF_SECTOR_MAP:
        return _ETF_SECTOR_MAP[ticker]

    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        return info.get("sector", "Unknown")
    except Exception:
        return "Unknown"


def map_portfolio(
    holdings: dict[str, float],
) -> tuple[dict[str, str], dict[str, str]]:
    """Resolve country and sector for all holdings.

    Returns:
        (country_map, sector_map) — both ticker -> string dicts
    """
    country_map = {}
    sector_map = {}

    for ticker in holdings:
        country_map[ticker] = resolve_country(ticker)
        sector_map[ticker] = resolve_sector(ticker)

    return country_map, sector_map
