"""Country registry for multi-country macro analysis."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Country:
    iso3: str           # ISO 3166-1 alpha-3
    name: str
    wb_code: str        # World Bank country code (usually same as iso3)
    market_index: str   # Primary equity index ticker (yfinance)
    currency: str       # ISO 4217 currency code
    fred_prefix: str    # Prefix for OECD series on FRED (if any)


COUNTRIES: dict[str, Country] = {}


def _register(*countries: Country) -> None:
    for c in countries:
        COUNTRIES[c.iso3] = c


_register(
    Country(
        iso3="USA", name="United States", wb_code="USA",
        market_index="^GSPC", currency="USD", fred_prefix="",
    ),
    Country(
        iso3="GBR", name="United Kingdom", wb_code="GBR",
        market_index="^FTSE", currency="GBP", fred_prefix="GBR",
    ),
    Country(
        iso3="DEU", name="Germany", wb_code="DEU",
        market_index="^GDAXI", currency="EUR", fred_prefix="DEU",
    ),
    Country(
        iso3="FRA", name="France", wb_code="FRA",
        market_index="^FCHI", currency="EUR", fred_prefix="FRA",
    ),
    Country(
        iso3="JPN", name="Japan", wb_code="JPN",
        market_index="^N225", currency="JPY", fred_prefix="JPN",
    ),
    Country(
        iso3="CAN", name="Canada", wb_code="CAN",
        market_index="^GSPTSE", currency="CAD", fred_prefix="CAN",
    ),
    Country(
        iso3="ITA", name="Italy", wb_code="ITA",
        market_index="FTSEMIB.MI", currency="EUR", fred_prefix="ITA",
    ),
    Country(
        iso3="AUS", name="Australia", wb_code="AUS",
        market_index="^AXJO", currency="AUD", fred_prefix="AUS",
    ),
    Country(
        iso3="CHN", name="China", wb_code="CHN",
        market_index="000001.SS", currency="CNY", fred_prefix="CHN",
    ),
    Country(
        iso3="IND", name="India", wb_code="IND",
        market_index="^BSESN", currency="INR", fred_prefix="IND",
    ),
    Country(
        iso3="BRA", name="Brazil", wb_code="BRA",
        market_index="^BVSP", currency="BRL", fred_prefix="BRA",
    ),
    Country(
        iso3="KOR", name="South Korea", wb_code="KOR",
        market_index="^KS11", currency="KRW", fred_prefix="KOR",
    ),
)

# Default analysis set
G7_COUNTRIES = ["USA", "GBR", "DEU", "FRA", "JPN", "CAN", "ITA"]
G20_MAJOR = G7_COUNTRIES + ["AUS", "CHN", "IND", "BRA", "KOR"]
