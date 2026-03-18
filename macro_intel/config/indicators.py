"""Extended indicator registry: FRED macroeconomic + World Bank structural indicators.

Adapted from econ-monitor's indicator registry with added country_scope and
World Bank indicator definitions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Indicator:
    name: str           # Human-readable name
    series_id: str      # FRED series ID or WB indicator code
    source: str         # "fred" | "worldbank" | "market"
    category: str       # Grouping category
    frequency: str      # monthly | weekly | quarterly | daily | annual
    unit: str           # index | percent | thousands | millions | billions | ratio | dollars
    transform: str      # How to display: level | yoy_pct | mom_pct | net_change | annualized
    higher_is: str      # inflationary | expansionary | contractionary | neutral
    country_scope: str  # "USA" for US-only FRED, "*" for all countries (WB)
    description: str    # Short description


INDICATORS: dict[str, Indicator] = {}


def _register(*indicators: Indicator) -> None:
    for ind in indicators:
        INDICATORS[ind.series_id] = ind


# ── FRED: Inflation ──────────────────────────────────────────────────────────
_register(
    Indicator("CPI (All Urban)", "CPIAUCSL", "fred", "Inflation", "monthly",
              "index", "yoy_pct", "inflationary", "USA",
              "Consumer Price Index for All Urban Consumers, SA"),
    Indicator("Core CPI", "CPILFESL", "fred", "Inflation", "monthly",
              "index", "yoy_pct", "inflationary", "USA",
              "CPI excluding food and energy, SA"),
    Indicator("PPI (Final Demand)", "PPIFIS", "fred", "Inflation", "monthly",
              "index", "yoy_pct", "inflationary", "USA",
              "Producer Price Index for Final Demand, SA"),
    Indicator("PCE Price Index", "PCEPI", "fred", "Inflation", "monthly",
              "index", "yoy_pct", "inflationary", "USA",
              "Personal Consumption Expenditures Price Index"),
    Indicator("Core PCE", "PCEPILFE", "fred", "Inflation", "monthly",
              "index", "yoy_pct", "inflationary", "USA",
              "PCE excluding food and energy (Fed preferred gauge)"),
)

# ── FRED: Labor ──────────────────────────────────────────────────────────────
_register(
    Indicator("Nonfarm Payrolls", "PAYEMS", "fred", "Labor", "monthly",
              "thousands", "net_change", "expansionary", "USA",
              "Total nonfarm employees, SA"),
    Indicator("Unemployment Rate", "UNRATE", "fred", "Labor", "monthly",
              "percent", "level", "contractionary", "USA",
              "Civilian unemployment rate, SA"),
    Indicator("Initial Jobless Claims", "ICSA", "fred", "Labor", "weekly",
              "thousands", "level", "contractionary", "USA",
              "Initial claims for unemployment insurance, SA"),
    Indicator("JOLTS Job Openings", "JTSJOL", "fred", "Labor", "monthly",
              "thousands", "level", "expansionary", "USA",
              "Total job openings, SA"),
    Indicator("Labor Force Participation", "CIVPART", "fred", "Labor", "monthly",
              "percent", "level", "expansionary", "USA",
              "Labor force participation rate"),
    Indicator("Average Hourly Earnings", "CES0500000003", "fred", "Labor", "monthly",
              "dollars", "yoy_pct", "inflationary", "USA",
              "Average hourly earnings of all private employees"),
)

# ── FRED: Output ─────────────────────────────────────────────────────────────
_register(
    Indicator("Real GDP", "GDPC1", "fred", "Output", "quarterly",
              "billions", "annualized", "expansionary", "USA",
              "Real GDP, SAAR"),
    Indicator("Industrial Production", "INDPRO", "fred", "Output", "monthly",
              "index", "yoy_pct", "expansionary", "USA",
              "Industrial Production Index, SA"),
    Indicator("Capacity Utilization", "TCU", "fred", "Output", "monthly",
              "percent", "level", "expansionary", "USA",
              "Total industry capacity utilization rate"),
)

# ── FRED: Consumer ───────────────────────────────────────────────────────────
_register(
    Indicator("Retail Sales", "RSAFS", "fred", "Consumer", "monthly",
              "millions", "mom_pct", "expansionary", "USA",
              "Advance retail sales, SA"),
    Indicator("UMich Consumer Sentiment", "UMCSENT", "fred", "Consumer", "monthly",
              "index", "level", "expansionary", "USA",
              "University of Michigan Consumer Sentiment Index"),
    Indicator("Personal Income", "PI", "fred", "Consumer", "monthly",
              "billions", "mom_pct", "expansionary", "USA",
              "Personal income, SAAR"),
    Indicator("Personal Spending (PCE)", "PCE", "fred", "Consumer", "monthly",
              "billions", "mom_pct", "expansionary", "USA",
              "Personal consumption expenditures, SAAR"),
    Indicator("Personal Saving Rate", "PSAVERT", "fred", "Consumer", "monthly",
              "percent", "level", "neutral", "USA",
              "Personal saving as pct of disposable income"),
)

# ── FRED: Business ───────────────────────────────────────────────────────────
_register(
    Indicator("ISM Manufacturing PMI", "MANEMP", "fred", "Business", "monthly",
              "index", "level", "expansionary", "USA",
              "ISM Manufacturing Employment Index (PMI proxy)"),
    Indicator("Durable Goods Orders", "DGORDER", "fred", "Business", "monthly",
              "millions", "mom_pct", "expansionary", "USA",
              "Manufacturers' new orders for durable goods, SA"),
)

# ── FRED: Housing ────────────────────────────────────────────────────────────
_register(
    Indicator("Housing Starts", "HOUST", "fred", "Housing", "monthly",
              "thousands", "level", "expansionary", "USA",
              "New privately-owned housing units started, SAAR"),
    Indicator("Building Permits", "PERMIT", "fred", "Housing", "monthly",
              "thousands", "level", "expansionary", "USA",
              "New private housing units authorized, SAAR"),
    Indicator("Case-Shiller Home Price Index", "CSUSHPINSA", "fred", "Housing", "monthly",
              "index", "yoy_pct", "inflationary", "USA",
              "S&P/Case-Shiller U.S. National Home Price Index, NSA"),
)

# ── FRED: Trade ──────────────────────────────────────────────────────────────
_register(
    Indicator("Trade Balance", "BOPGSTB", "fred", "Trade", "monthly",
              "millions", "level", "neutral", "USA",
              "Balance on goods and services, BOP basis"),
)

# ── FRED: Monetary Policy ───────────────────────────────────────────────────
_register(
    Indicator("Federal Funds Rate", "FEDFUNDS", "fred", "Monetary", "monthly",
              "percent", "level", "contractionary", "USA",
              "Effective federal funds rate"),
    Indicator("M2 Money Supply", "M2SL", "fred", "Monetary", "monthly",
              "billions", "yoy_pct", "inflationary", "USA",
              "M2 money stock, SA"),
)

# ── FRED: Fixed Income / Yield Curve ─────────────────────────────────────────
_register(
    Indicator("10Y-2Y Treasury Spread", "T10Y2Y", "fred", "Fixed Income", "daily",
              "percent", "level", "expansionary", "USA",
              "10Y minus 2Y Treasury constant maturity spread"),
    Indicator("10Y-3M Treasury Spread", "T10Y3M", "fred", "Fixed Income", "daily",
              "percent", "level", "expansionary", "USA",
              "10Y minus 3M Treasury constant maturity spread"),
    Indicator("HY Credit Spread", "BAMLH0A0HYM2", "fred", "Fixed Income", "daily",
              "percent", "level", "contractionary", "USA",
              "ICE BofA US High Yield Option-Adjusted Spread"),
    Indicator("10-Year Treasury Yield", "DGS10", "fred", "Fixed Income", "daily",
              "percent", "level", "neutral", "USA",
              "10-year constant maturity Treasury yield"),
    Indicator("2-Year Treasury Yield", "DGS2", "fred", "Fixed Income", "daily",
              "percent", "level", "neutral", "USA",
              "2-year constant maturity Treasury yield"),
)

# ── FRED: Market Stress ──────────────────────────────────────────────────────
_register(
    Indicator("VIX", "VIXCLS", "fred", "Market", "daily",
              "index", "level", "contractionary", "USA",
              "CBOE Volatility Index"),
    Indicator("Trade-Weighted Dollar", "DTWEXBGS", "fred", "Market", "daily",
              "index", "level", "neutral", "USA",
              "Nominal Broad U.S. Dollar Index"),
)

# ── FRED: Recession Indicator ────────────────────────────────────────────────
_register(
    Indicator("NBER Recession Indicator", "USREC", "fred", "Regime", "monthly",
              "binary", "level", "contractionary", "USA",
              "NBER recession indicator (1=recession, 0=expansion)"),
)

# ── World Bank: Structural / Cross-Country ───────────────────────────────────
_register(
    Indicator("GDP Growth", "NY.GDP.MKTP.KD.ZG", "worldbank", "Output", "annual",
              "percent", "level", "expansionary", "*",
              "GDP growth rate (annual %)"),
    Indicator("GDP per Capita PPP", "NY.GDP.PCAP.PP.KD", "worldbank", "Output", "annual",
              "dollars", "level", "expansionary", "*",
              "GDP per capita, PPP (constant 2017 international $)"),
    Indicator("CPI Inflation", "FP.CPI.TOTL.ZG", "worldbank", "Inflation", "annual",
              "percent", "level", "inflationary", "*",
              "Inflation, consumer prices (annual %)"),
    Indicator("Trade (% of GDP)", "NE.TRD.GNFS.ZS", "worldbank", "Trade", "annual",
              "percent", "level", "neutral", "*",
              "Trade as percentage of GDP"),
    Indicator("Current Account (% GDP)", "BN.CAB.XOKA.GD.ZS", "worldbank", "Trade", "annual",
              "percent", "level", "neutral", "*",
              "Current account balance (% of GDP)"),
    Indicator("Govt Debt (% GDP)", "GC.DOD.TOTL.GD.ZS", "worldbank", "Fiscal", "annual",
              "percent", "level", "neutral", "*",
              "Central government debt, total (% of GDP)"),
    Indicator("Broad Money (% GDP)", "FM.LBL.BMNY.GD.ZS", "worldbank", "Monetary", "annual",
              "percent", "level", "neutral", "*",
              "Broad money (% of GDP)"),
    Indicator("Real Interest Rate", "FR.INR.RINR", "worldbank", "Monetary", "annual",
              "percent", "level", "neutral", "*",
              "Real interest rate (%)"),
    Indicator("Unemployment (ILO)", "SL.UEM.TOTL.ZS", "worldbank", "Labor", "annual",
              "percent", "level", "contractionary", "*",
              "Unemployment, total (% of labor force, ILO estimate)"),
    Indicator("Industry Value Added (% GDP)", "NV.IND.TOTL.ZS", "worldbank", "Output", "annual",
              "percent", "level", "neutral", "*",
              "Industry (including construction), value added (% of GDP)"),
    Indicator("Gross Capital Formation (% GDP)", "NE.GDI.FTOT.ZS", "worldbank", "Output", "annual",
              "percent", "level", "expansionary", "*",
              "Gross fixed capital formation (% of GDP)"),
    Indicator("FDI Inflows (% GDP)", "BX.KLT.DINV.WD.GD.ZS", "worldbank", "Trade", "annual",
              "percent", "level", "expansionary", "*",
              "Foreign direct investment, net inflows (% of GDP)"),
    Indicator("Population Growth", "SP.POP.GROW", "worldbank", "Structural", "annual",
              "percent", "level", "neutral", "*",
              "Population growth (annual %)"),
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_fred_indicators() -> dict[str, Indicator]:
    """Return only FRED-sourced indicators."""
    return {k: v for k, v in INDICATORS.items() if v.source == "fred"}


def get_wb_indicators() -> dict[str, Indicator]:
    """Return only World Bank-sourced indicators."""
    return {k: v for k, v in INDICATORS.items() if v.source == "worldbank"}


def get_indicators_by_category() -> dict[str, list[Indicator]]:
    """Return indicators grouped by category."""
    groups: dict[str, list[Indicator]] = {}
    for ind in INDICATORS.values():
        groups.setdefault(ind.category, []).append(ind)
    return groups


# Feature columns used by the regime model (subset of key macro indicators)
REGIME_FEATURES: list[str] = [
    # FRED
    "CPIAUCSL", "CPILFESL", "UNRATE", "PAYEMS", "ICSA",
    "GDPC1", "INDPRO", "TCU", "RSAFS", "UMCSENT",
    "T10Y2Y", "BAMLH0A0HYM2", "VIXCLS", "FEDFUNDS", "M2SL",
    "DGS10", "DGS2",
    # World Bank (cross-country)
    "NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG", "SL.UEM.TOTL.ZS",
    "BN.CAB.XOKA.GD.ZS", "GC.DOD.TOTL.GD.ZS",
]

CATEGORY_ORDER = [
    "Inflation", "Labor", "Output", "Consumer", "Business",
    "Housing", "Trade", "Monetary", "Fiscal", "Fixed Income",
    "Market", "Structural", "Regime",
]
