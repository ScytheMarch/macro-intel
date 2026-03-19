"""Map portfolio holdings to country, sector, and factor exposures.

Uses hardcoded mappings for common ETFs/funds and yfinance as fallback.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── ETF → Country mappings ────────────────────────────────────────────────
_ETF_COUNTRY_MAP: dict[str, str] = {
    # US broad market
    "SPY": "USA", "VOO": "USA", "VTI": "USA", "QQQ": "USA", "IWM": "USA",
    "IVV": "USA", "DIA": "USA", "RSP": "USA", "SPLG": "USA", "SCHB": "USA",
    "ITOT": "USA", "SPTM": "USA", "MGK": "USA", "VUG": "USA", "VTV": "USA",
    "SCHG": "USA", "SCHV": "USA", "IWF": "USA", "IWD": "USA",

    # International developed
    "EFA": "International Developed", "VXUS": "International",
    "VEA": "International Developed", "IEFA": "International Developed",
    "IXUS": "International", "SCHF": "International Developed",
    "SPDW": "International Developed",

    # Emerging markets
    "EEM": "Emerging Markets", "VWO": "Emerging Markets",
    "IEMG": "Emerging Markets", "SCHE": "Emerging Markets",

    # Single country
    "EWJ": "Japan", "EWG": "Germany", "EWU": "United Kingdom",
    "EWC": "Canada", "FXI": "China", "EWZ": "Brazil",
    "EWY": "South Korea", "EWA": "Australia", "INDA": "India",
    "EWI": "Italy", "EWQ": "France", "EWH": "Hong Kong",
    "EWT": "Taiwan", "EWS": "Singapore", "EWP": "Spain",
    "EWN": "Netherlands", "EWD": "Sweden", "EWL": "Switzerland",
    "EWK": "Belgium", "EIS": "Israel", "TUR": "Turkey",
    "THD": "Thailand", "EPOL": "Poland", "ECH": "Chile",

    # Fixed income — country = issuer
    "BND": "USA", "AGG": "USA", "TLT": "USA", "SHY": "USA",
    "IEF": "USA", "TIP": "USA", "BNDX": "International",
    "EMB": "Emerging Markets", "LQD": "USA", "HYG": "USA",
    "JNK": "USA", "VCSH": "USA", "VCIT": "USA", "VGSH": "USA",
    "GOVT": "USA", "MUB": "USA", "VTIP": "USA", "SCHZ": "USA",
    "BIV": "USA", "BSV": "USA", "BLV": "USA",

    # Commodities / alternatives
    "GLD": "Global", "SLV": "Global", "USO": "Global",
    "IAU": "Global", "DBC": "Global", "GSG": "Global",
    "PDBC": "Global", "GLDM": "Global", "SGOL": "Global",

    # Real estate
    "VNQ": "USA", "VNQI": "International", "IYR": "USA",
    "SCHH": "USA", "RWX": "International", "XLRE": "USA",
}

# ── ETF → Sector mappings ─────────────────────────────────────────────────
_ETF_SECTOR_MAP: dict[str, str] = {
    # Sector ETFs
    "XLK": "Technology", "VGT": "Technology", "FTEC": "Technology",
    "XLF": "Financials", "VFH": "Financials",
    "XLV": "Healthcare", "VHT": "Healthcare",
    "XLE": "Energy", "VDE": "Energy",
    "XLI": "Industrials", "VIS": "Industrials",
    "XLP": "Consumer Staples", "VDC": "Consumer Staples",
    "XLY": "Consumer Discretionary", "VCR": "Consumer Discretionary",
    "XLU": "Utilities", "VPU": "Utilities",
    "XLRE": "Real Estate", "VNQ": "Real Estate", "IYR": "Real Estate",
    "VNQI": "Real Estate", "SCHH": "Real Estate", "RWX": "Real Estate",
    "XLC": "Communication Services", "VOX": "Communication Services",
    "XLB": "Materials", "VAW": "Materials",

    # Broad market — multi-sector
    "SPY": "Broad Market (Multi-Sector)", "VOO": "Broad Market (Multi-Sector)",
    "VTI": "Broad Market (Multi-Sector)", "QQQ": "Technology-Heavy Growth",
    "IWM": "Small Cap (Multi-Sector)", "IVV": "Broad Market (Multi-Sector)",
    "DIA": "Blue Chip (Multi-Sector)", "RSP": "Equal Weight (Multi-Sector)",
    "SPLG": "Broad Market (Multi-Sector)", "SCHB": "Broad Market (Multi-Sector)",
    "ITOT": "Broad Market (Multi-Sector)", "VUG": "Growth (Multi-Sector)",
    "VTV": "Value (Multi-Sector)", "IWF": "Growth (Multi-Sector)",
    "IWD": "Value (Multi-Sector)", "SCHG": "Growth (Multi-Sector)",
    "SCHV": "Value (Multi-Sector)", "MGK": "Mega Cap Growth",

    # International — multi-sector
    "EFA": "International Equity", "VXUS": "International Equity",
    "VEA": "International Developed Equity", "IEFA": "International Developed Equity",
    "IXUS": "International Equity", "SCHF": "International Developed Equity",
    "EEM": "Emerging Market Equity", "VWO": "Emerging Market Equity",
    "IEMG": "Emerging Market Equity", "SCHE": "Emerging Market Equity",

    # Fixed income
    "BND": "Total Bond Market", "AGG": "Total Bond Market",
    "TLT": "Long-Term Treasuries", "SHY": "Short-Term Treasuries",
    "IEF": "Intermediate Treasuries", "TIP": "Inflation-Protected Bonds",
    "BNDX": "International Bonds", "EMB": "Emerging Market Bonds",
    "LQD": "Investment Grade Corporate", "HYG": "High Yield Corporate",
    "JNK": "High Yield Corporate", "VCSH": "Short-Term Corporate",
    "VCIT": "Intermediate Corporate", "VGSH": "Short-Term Treasuries",
    "GOVT": "US Treasuries", "MUB": "Municipal Bonds",
    "VTIP": "Short-Term TIPS", "SCHZ": "Total Bond Market",
    "BIV": "Intermediate Bonds", "BSV": "Short-Term Bonds",
    "BLV": "Long-Term Bonds",

    # Commodities / alternatives
    "GLD": "Gold", "IAU": "Gold", "GLDM": "Gold", "SGOL": "Gold",
    "SLV": "Silver", "USO": "Oil",
    "DBC": "Broad Commodities", "GSG": "Broad Commodities",
    "PDBC": "Broad Commodities",

    # Single country
    "EWJ": "Japanese Equity", "EWG": "German Equity",
    "EWU": "UK Equity", "EWC": "Canadian Equity",
    "FXI": "Chinese Equity", "EWZ": "Brazilian Equity",
    "EWY": "South Korean Equity", "EWA": "Australian Equity",
    "INDA": "Indian Equity", "EWI": "Italian Equity",
    "EWQ": "French Equity",
}


def resolve_country(ticker: str) -> str:
    """Resolve a ticker to its primary country exposure."""
    ticker = ticker.upper()
    if ticker in _ETF_COUNTRY_MAP:
        return _ETF_COUNTRY_MAP[ticker]

    # Try yfinance for individual stocks
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        country = info.get("country", "")
        if country:
            return country  # Use the full country name
    except Exception:
        pass

    return "USA"  # Default assumption for US-listed stocks


def resolve_sector(ticker: str) -> str:
    """Resolve a ticker to its sector."""
    ticker = ticker.upper()
    if ticker in _ETF_SECTOR_MAP:
        return _ETF_SECTOR_MAP[ticker]

    # Try yfinance for individual stocks
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        sector = info.get("sector", "")
        if sector:
            return sector
        # For ETFs, try category
        category = info.get("category", "")
        if category:
            return category
    except Exception:
        pass

    return "Equity"  # Better default than "Unknown"


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
