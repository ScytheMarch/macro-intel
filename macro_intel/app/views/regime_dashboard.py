"""Regime Dashboard — real-time macro regime monitoring with educational context."""

from __future__ import annotations

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ── Indicator metadata for regime signals ─────────────────────────────────────

REGIME_SIGNALS = {
    "UNRATE":       {"label": "Unemployment Rate",      "cat": "Labor",        "unit": "percent",   "higher_is": "contractionary",
                     "explain": "The percentage of people actively looking for work who can't find a job. Below 4.5% signals a strong job market."},
    "CPIAUCSL":     {"label": "CPI YoY",                "cat": "Inflation",    "unit": "percent",   "higher_is": "inflationary",
                     "explain": "How much prices have risen compared to a year ago. The Fed targets 2% — above 3.5% is considered hot inflation."},
    "CPILFESL":     {"label": "Core CPI YoY",           "cat": "Inflation",    "unit": "percent",   "higher_is": "inflationary",
                     "explain": "Inflation excluding food and energy (which are volatile). This is the 'true' underlying inflation trend."},
    "PAYEMS":       {"label": "Nonfarm Payrolls MoM",   "cat": "Labor",        "unit": "thousands", "higher_is": "expansionary",
                     "explain": "How many jobs the economy added (or lost) last month, in thousands. Above +150K/month is considered healthy growth."},
    "ICSA":         {"label": "Initial Jobless Claims",  "cat": "Labor",        "unit": "thousands", "higher_is": "contractionary",
                     "explain": "How many people filed for unemployment benefits this week. Below 230K means few layoffs; above 300K signals trouble."},
    "T10Y2Y":       {"label": "Yield Curve (10Y-2Y)",   "cat": "Fixed Income", "unit": "percent",   "higher_is": "expansionary",
                     "explain": "The gap between 10-year and 2-year Treasury yields. When this goes NEGATIVE (inverted), it has predicted every recession since 1970."},
    "FEDFUNDS":     {"label": "Fed Funds Rate",         "cat": "Monetary",     "unit": "percent",   "higher_is": "contractionary",
                     "explain": "The interest rate the Fed charges banks. Higher rates = Fed is fighting inflation. Lower rates = Fed is stimulating growth."},
    "VIXCLS":       {"label": "VIX (Fear Index)",       "cat": "Market",       "unit": "index",     "higher_is": "contractionary",
                     "explain": "Wall Street's 'fear gauge' — measures expected stock market volatility. Below 18 = calm markets. Above 30 = panic."},
    "BAMLH0A0HYM2": {"label": "HY Credit Spread",      "cat": "Fixed Income", "unit": "percent",   "higher_is": "contractionary",
                     "explain": "The extra interest risky companies pay to borrow vs the US government. Wider spreads = investors are scared about defaults."},
    "UMCSENT":      {"label": "Consumer Sentiment",     "cat": "Consumer",     "unit": "index",     "higher_is": "expansionary",
                     "explain": "Survey of how Americans feel about the economy. Above 80 = optimistic, people spend more. Below 60 = pessimistic, people save more."},
    "INDPRO":       {"label": "Industrial Production YoY", "cat": "Output",    "unit": "percent",   "higher_is": "expansionary",
                     "explain": "How much factories, mines, and utilities produced vs a year ago. Positive = economy growing. Negative = output shrinking."},
    "RSAFS":        {"label": "Retail Sales MoM",       "cat": "Consumer",     "unit": "percent",   "higher_is": "expansionary",
                     "explain": "How much Americans spent at stores last month vs the month before. Consumer spending drives ~70% of the US economy."},
    "GDPC1":        {"label": "Real GDP QoQ",           "cat": "Output",       "unit": "percent",   "higher_is": "expansionary",
                     "explain": "The total economic output of the US, adjusted for inflation. Two consecutive negative quarters = a recession."},
    "DGS10":        {"label": "10Y Treasury Yield",     "cat": "Fixed Income", "unit": "percent",   "higher_is": "neutral",
                     "explain": "The return on lending money to the US government for 10 years. This sets the benchmark for mortgage rates and corporate borrowing."},
    "DGS2":         {"label": "2Y Treasury Yield",      "cat": "Fixed Income", "unit": "percent",   "higher_is": "neutral",
                     "explain": "The return on lending to the government for 2 years. Tracks closely with where the market thinks the Fed will set rates."},
    "M2SL":         {"label": "M2 Money Supply YoY",    "cat": "Monetary",     "unit": "percent",   "higher_is": "inflationary",
                     "explain": "How fast the total money in the economy is growing. Rapid growth can fuel inflation; shrinking money supply slows the economy."},
    "HOUST":        {"label": "Housing Starts",         "cat": "Housing",      "unit": "thousands", "higher_is": "expansionary",
                     "explain": "How many new homes started construction this month. Housing is a leading indicator — builders only build when they're confident."},
    "TCU":          {"label": "Capacity Utilization",   "cat": "Output",       "unit": "percent",   "higher_is": "expansionary",
                     "explain": "What percentage of factory capacity is being used. Above 80% = economy running hot. Below 75% = lots of slack."},
    "PSAVERT":      {"label": "Personal Saving Rate",   "cat": "Consumer",     "unit": "percent",   "higher_is": "neutral",
                     "explain": "What percentage of income Americans are saving instead of spending. High saving = cautious consumers. Low saving = confidence (or stress)."},
}

# Which series need YoY transforms
YOY_SERIES = {"CPIAUCSL", "CPILFESL", "INDPRO", "M2SL"}
MOM_SERIES = {"PAYEMS", "RSAFS"}
QOQ_SERIES = {"GDPC1"}

# Plain-English regime explanations
REGIME_EXPLANATIONS = {
    "Expansion": {
        "summary": "The economy is growing and healthy",
        "detail": "Jobs are plentiful, businesses are hiring, consumers are spending, and markets are calm. "
                  "This is the 'goldilocks' state where growth is strong but inflation is under control.",
        "what_to_watch": "Watch for rising inflation or an inverting yield curve — these often signal the end of an expansion.",
        "historical": "The US economy spends about 70-80% of the time in expansion. The longest expansion lasted from 2009 to 2020 (128 months).",
    },
    "Slowdown": {
        "summary": "Growth is losing momentum",
        "detail": "The economy is still growing, but the pace is slowing. Some indicators are weakening — maybe hiring is slowing, "
                  "consumer confidence is dipping, or manufacturing is softening. This doesn't always lead to recession.",
        "what_to_watch": "If the yield curve inverts and credit spreads widen simultaneously, the odds of recession increase significantly.",
        "historical": "Many slowdowns are just 'mid-cycle pauses' — the economy catches its breath and re-accelerates without entering recession.",
    },
    "Contraction": {
        "summary": "The economy is shrinking",
        "detail": "Multiple indicators are flashing red: unemployment is rising, production is falling, and businesses are pulling back. "
                  "If sustained, this is likely a recession. The Fed typically responds by cutting interest rates.",
        "what_to_watch": "Watch for stabilization in jobless claims and the yield curve — these are often the first signs the worst is over.",
        "historical": "Since WWII, the average recession lasts about 11 months. The 2008 financial crisis lasted 18 months; the COVID recession only 2 months.",
    },
    "Crisis": {
        "summary": "Severe economic stress",
        "detail": "This is a full-blown economic emergency: the VIX is spiking, credit markets are freezing, layoffs are surging, "
                  "and fear is everywhere. This state is rare but intense — think March 2020 or September 2008.",
        "what_to_watch": "Massive fiscal and monetary intervention usually follows. Markets often bottom and recover before the economy does.",
        "historical": "True crisis periods are rare (only ~5% of the time) but produce the sharpest market moves in both directions.",
    },
    "Unknown": {
        "summary": "Insufficient data to classify",
        "detail": "Not enough indicators are available to determine the current economic regime. Fetch more data to get a reading.",
        "what_to_watch": "Click 'Fetch Data' to pull the latest economic indicators.",
        "historical": "",
    },
}

# Z-score explanations
ZSCORE_EXPLAIN = (
    "**What is a Z-Score?** It measures how unusual a reading is compared to its own history. "
    "A Z-score of 0 means 'perfectly normal.' ±1 is a moderate move. ±2 is rare (happens ~5% of the time). "
    "Beyond ±2.5 is extreme — something significant is happening."
)


def _compute_z(series: pd.Series, window: int = 60) -> float | None:
    if len(series) < 12:
        return None
    w = min(window, len(series))
    recent = series.tail(w)
    mean, std = recent.mean(), recent.std()
    if std == 0 or pd.isna(std):
        return None
    return float((series.iloc[-1] - mean) / std)


def _trend_direction(series: pd.Series, lookback: int = 6) -> str:
    if len(series) < lookback + 1:
        return "stable"
    recent = series.tail(lookback)
    std = recent.std()
    if std == 0 or pd.isna(std):
        return "stable"
    slope = np.polyfit(range(len(recent)), recent.values, 1)[0]
    if slope > 0.01 * std:
        return "improving"
    elif slope < -0.01 * std:
        return "deteriorating"
    return "stable"


def _classify_regime(signals: dict[str, dict]) -> tuple[str, str, float, dict[str, int], list[str]]:
    """Rules-based regime using BOTH current levels AND momentum/z-scores.

    Returns (name, color, confidence, vote_counts, rationale_list).
    """
    votes = {"Expansion": 0, "Slowdown": 0, "Contraction": 0, "Crisis": 0}
    rationale: list[str] = []
    total = 0

    def _vote(regime: str, reason: str):
        nonlocal total
        votes[regime] += 1
        total += 1
        rationale.append(reason)

    # ── Unemployment: level + trend ──────────────────────────────────────
    ur = signals.get("UNRATE", {})
    if ur.get("latest") is not None:
        val, z, trend = ur["latest"], ur.get("z_score", 0), ur.get("trend", "stable")
        if val < 4.5 and trend != "deteriorating":
            _vote("Expansion", f"Unemployment low at {val:.1f}% and stable")
        elif val < 4.5 and trend == "deteriorating":
            _vote("Slowdown", f"Unemployment low ({val:.1f}%) but rising — early warning")
        elif val < 6.0:
            _vote("Slowdown", f"Unemployment elevated at {val:.1f}%")
        else:
            _vote("Contraction", f"Unemployment high at {val:.1f}%")

    # ── Payrolls: momentum matters more than level ───────────────────────
    nfp = signals.get("PAYEMS", {})
    if nfp.get("latest") is not None:
        val, z = nfp["latest"], nfp.get("z_score", 0)
        if val > 200:
            _vote("Expansion", f"Strong hiring: +{val:.0f}K jobs/month")
        elif val > 100:
            _vote("Slowdown", f"Hiring slowing: +{val:.0f}K jobs/month")
        elif val > 0:
            _vote("Slowdown", f"Weak hiring: only +{val:.0f}K jobs/month")
        else:
            _vote("Contraction", f"Job losses: {val:.0f}K/month")
        # Extra vote if z-score is extreme
        if z is not None and z < -1.5:
            _vote("Contraction", f"Payrolls at {z:+.1f}σ — well below normal pace")

    # ── Yield curve: classic recession predictor ─────────────────────────
    yc = signals.get("T10Y2Y", {})
    if yc.get("latest") is not None:
        val, trend = yc["latest"], yc.get("trend", "stable")
        if val > 0.5:
            _vote("Expansion", f"Yield curve positive at {val:+.2f}% — healthy")
        elif val > 0:
            _vote("Slowdown", f"Yield curve flattening at {val:+.2f}% — watch closely")
        elif val > -0.5:
            _vote("Contraction", f"Yield curve inverted at {val:+.2f}% — recession signal")
        else:
            _vote("Crisis", f"Yield curve deeply inverted at {val:+.2f}%")

    # ── VIX: fear gauge ──────────────────────────────────────────────────
    vix = signals.get("VIXCLS", {})
    if vix.get("latest") is not None:
        val, z = vix["latest"], vix.get("z_score", 0)
        if val < 18:
            _vote("Expansion", f"VIX calm at {val:.1f} — markets relaxed")
        elif val < 25:
            _vote("Slowdown", f"VIX elevated at {val:.1f} — some nervousness")
        elif val < 35:
            _vote("Contraction", f"VIX high at {val:.1f} — significant fear")
        else:
            _vote("Crisis", f"VIX spiking at {val:.1f} — market panic")

    # ── Credit spreads: level + z-score ──────────────────────────────────
    hy = signals.get("BAMLH0A0HYM2", {})
    if hy.get("latest") is not None:
        val, z = hy["latest"], hy.get("z_score", 0)
        if val < 3.5 and (z is None or z < 1.0):
            _vote("Expansion", f"Credit spreads tight at {val:.2f}% — low default risk")
        elif val < 5.0:
            _vote("Slowdown", f"Credit spreads widening to {val:.2f}% — caution")
        elif val < 7.0:
            _vote("Contraction", f"Credit spreads wide at {val:.2f}% — stress in corporate bonds")
        else:
            _vote("Crisis", f"Credit spreads at {val:.2f}% — credit market freeze risk")
        # Extra vote if z-score shows rapid widening
        if z is not None and z > 1.5:
            _vote("Contraction", f"Credit spreads at {z:+.1f}σ — widening fast")

    # ── Jobless claims: level + trend ────────────────────────────────────
    claims = signals.get("ICSA", {})
    if claims.get("latest") is not None:
        val, trend = claims["latest"], claims.get("trend", "stable")
        if val < 230 and trend != "deteriorating":
            _vote("Expansion", f"Claims low at {val:.0f}K — few layoffs")
        elif val < 230 and trend == "deteriorating":
            _vote("Slowdown", f"Claims low ({val:.0f}K) but rising trend")
        elif val < 300:
            _vote("Slowdown", f"Claims rising to {val:.0f}K")
        elif val < 400:
            _vote("Contraction", f"Claims elevated at {val:.0f}K — layoffs increasing")
        else:
            _vote("Crisis", f"Claims surging at {val:.0f}K — mass layoffs")

    # ── Consumer sentiment ───────────────────────────────────────────────
    sent = signals.get("UMCSENT", {})
    if sent.get("latest") is not None:
        val, z = sent["latest"], sent.get("z_score", 0)
        if val > 80:
            _vote("Expansion", f"Consumers optimistic at {val:.1f}")
        elif val > 65:
            _vote("Slowdown", f"Consumer sentiment lukewarm at {val:.1f}")
        elif val > 50:
            _vote("Contraction", f"Consumers pessimistic at {val:.1f}")
        else:
            _vote("Crisis", f"Consumer sentiment deeply negative at {val:.1f}")

    # ── Industrial production: z-score for momentum ──────────────────────
    indpro = signals.get("INDPRO", {})
    if indpro.get("latest") is not None:
        val, z = indpro["latest"], indpro.get("z_score", 0)
        if val > 2.0:
            _vote("Expansion", f"Industrial production growing at {val:+.1f}% YoY")
        elif val > 0:
            _vote("Slowdown", f"Industrial production barely growing at {val:+.1f}% YoY")
        else:
            _vote("Contraction", f"Industrial production falling at {val:+.1f}% YoY")

    # ── Housing starts: leading indicator ────────────────────────────────
    houst = signals.get("HOUST", {})
    if houst.get("latest") is not None:
        val, z, trend = houst["latest"], houst.get("z_score", 0), houst.get("trend", "stable")
        if z is not None:
            if z < -1.0 or trend == "deteriorating":
                _vote("Slowdown", f"Housing starts weakening ({z:+.1f}σ) — builders pulling back")

    # ── Building permits: leading indicator ──────────────────────────────
    # Check from the raw REGIME_SIGNALS (PERMIT is not in our set but housing data captures it)

    # ── Fed funds: context-dependent ─────────────────────────────────────
    ff = signals.get("FEDFUNDS", {})
    if ff.get("latest") is not None:
        val, z, trend = ff["latest"], ff.get("z_score", 0), ff.get("trend", "stable")
        if z is not None and z > 1.5:
            _vote("Slowdown", f"Fed funds rate elevated at {val:.2f}% ({z:+.1f}σ) — tight policy weighing on growth")

    if total == 0:
        return "Unknown", "#6b7280", 0.0, votes, []

    regime = max(votes, key=votes.get)
    confidence = votes[regime] / total
    colors = {"Expansion": "#22c55e", "Slowdown": "#eab308", "Contraction": "#ef4444", "Crisis": "#dc2626"}
    return regime, colors[regime], confidence, votes, rationale


def _get_vote_mapping(signals: dict[str, dict]) -> list[tuple[str, str]]:
    """Return list of (regime_voted, reason) pairs for display."""
    mapping: list[tuple[str, str]] = []

    def _add(regime: str, reason: str):
        mapping.append((regime, reason))

    ur = signals.get("UNRATE", {})
    if ur.get("latest") is not None:
        val, trend = ur["latest"], ur.get("trend", "stable")
        if val < 4.5 and trend != "deteriorating":
            _add("Expansion", f"Unemployment low at {val:.1f}% and stable")
        elif val < 4.5 and trend == "deteriorating":
            _add("Slowdown", f"Unemployment low ({val:.1f}%) but rising — early warning")
        elif val < 6.0:
            _add("Slowdown", f"Unemployment elevated at {val:.1f}%")
        else:
            _add("Contraction", f"Unemployment high at {val:.1f}%")

    nfp = signals.get("PAYEMS", {})
    if nfp.get("latest") is not None:
        val, z = nfp["latest"], nfp.get("z_score", 0)
        if val > 200:
            _add("Expansion", f"Strong hiring: +{val:.0f}K jobs/month")
        elif val > 100:
            _add("Slowdown", f"Hiring slowing: +{val:.0f}K jobs/month")
        elif val > 0:
            _add("Slowdown", f"Weak hiring: only +{val:.0f}K jobs/month")
        else:
            _add("Contraction", f"Job losses: {val:.0f}K/month")
        if z is not None and z < -1.5:
            _add("Contraction", f"Payrolls at {z:+.1f}σ — well below normal pace")

    yc = signals.get("T10Y2Y", {})
    if yc.get("latest") is not None:
        val = yc["latest"]
        if val > 0.5:
            _add("Expansion", f"Yield curve positive at {val:+.2f}% — healthy")
        elif val > 0:
            _add("Slowdown", f"Yield curve flattening at {val:+.2f}% — watch closely")
        elif val > -0.5:
            _add("Contraction", f"Yield curve inverted at {val:+.2f}% — recession signal")
        else:
            _add("Crisis", f"Yield curve deeply inverted at {val:+.2f}%")

    vix = signals.get("VIXCLS", {})
    if vix.get("latest") is not None:
        val = vix["latest"]
        if val < 18:
            _add("Expansion", f"VIX calm at {val:.1f} — markets relaxed")
        elif val < 25:
            _add("Slowdown", f"VIX elevated at {val:.1f} — some nervousness")
        elif val < 35:
            _add("Contraction", f"VIX high at {val:.1f} — significant fear")
        else:
            _add("Crisis", f"VIX spiking at {val:.1f} — market panic")

    hy = signals.get("BAMLH0A0HYM2", {})
    if hy.get("latest") is not None:
        val, z = hy["latest"], hy.get("z_score", 0)
        if val < 3.5 and (z is None or z < 1.0):
            _add("Expansion", f"Credit spreads tight at {val:.2f}% — low default risk")
        elif val < 5.0:
            _add("Slowdown", f"Credit spreads widening to {val:.2f}% — caution")
        elif val < 7.0:
            _add("Contraction", f"Credit spreads wide at {val:.2f}% — stress in corporate bonds")
        else:
            _add("Crisis", f"Credit spreads at {val:.2f}% — credit market freeze risk")
        if z is not None and z > 1.5:
            _add("Contraction", f"Credit spreads at {z:+.1f}σ — widening fast")

    claims = signals.get("ICSA", {})
    if claims.get("latest") is not None:
        val, trend = claims["latest"], claims.get("trend", "stable")
        if val < 230 and trend != "deteriorating":
            _add("Expansion", f"Claims low at {val:.0f}K — few layoffs")
        elif val < 230 and trend == "deteriorating":
            _add("Slowdown", f"Claims low ({val:.0f}K) but rising trend")
        elif val < 300:
            _add("Slowdown", f"Claims rising to {val:.0f}K")
        elif val < 400:
            _add("Contraction", f"Claims elevated at {val:.0f}K — layoffs increasing")
        else:
            _add("Crisis", f"Claims surging at {val:.0f}K — mass layoffs")

    sent = signals.get("UMCSENT", {})
    if sent.get("latest") is not None:
        val = sent["latest"]
        if val > 80:
            _add("Expansion", f"Consumers optimistic at {val:.1f}")
        elif val > 65:
            _add("Slowdown", f"Consumer sentiment lukewarm at {val:.1f}")
        elif val > 50:
            _add("Contraction", f"Consumers pessimistic at {val:.1f}")
        else:
            _add("Crisis", f"Consumer sentiment deeply negative at {val:.1f}")

    indpro = signals.get("INDPRO", {})
    if indpro.get("latest") is not None:
        val = indpro["latest"]
        if val > 2.0:
            _add("Expansion", f"Industrial production growing at {val:+.1f}% YoY")
        elif val > 0:
            _add("Slowdown", f"Industrial production barely growing at {val:+.1f}% YoY")
        else:
            _add("Contraction", f"Industrial production falling at {val:+.1f}% YoY")

    houst = signals.get("HOUST", {})
    if houst.get("latest") is not None:
        z, trend = houst.get("z_score", 0), houst.get("trend", "stable")
        if z is not None and (z < -1.0 or trend == "deteriorating"):
            _add("Slowdown", f"Housing starts weakening ({z:+.1f}σ) — builders pulling back")

    ff = signals.get("FEDFUNDS", {})
    if ff.get("latest") is not None:
        val, z = ff["latest"], ff.get("z_score", 0)
        if z is not None and z > 1.5:
            _add("Slowdown", f"Fed funds rate elevated at {val:.2f}% ({z:+.1f}σ) — tight policy")

    return mapping


def render():
    from macro_intel.app.styles import (
        glass_card, section_header, badge, metric_card,
        trend_color, trend_arrow, z_color, format_value,
        CATEGORY_COLORS, GREEN, YELLOW, RED, GRAY, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    )
    from macro_intel.config.indicators import get_fred_indicators
    from macro_intel.data import cache, fred_client

    # ── Title ─────────────────────────────────────────────────────────────
    st.markdown(
        '<h2 style="margin:0 0 4px 0;font-weight:800;letter-spacing:-0.5px">'
        '🧠 <span style="background:linear-gradient(135deg,#818cf8,#a78bfa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent">'
        'Regime Dashboard</span></h2>'
        f'<div style="color:{TEXT_MUTED};font-size:0.78em;letter-spacing:0.3px;'
        f'margin-bottom:4px">Real-time macro regime classification · '
        f'Rules-based signal aggregation</div>',
        unsafe_allow_html=True,
    )

    # Educational intro
    with st.expander("ℹ️ How to read this dashboard", expanded=False):
        st.markdown("""
**What is a "regime"?**
The economy moves through cycles — growth, slowdown, recession, recovery. This dashboard analyzes 19 key economic indicators
in real-time and uses a rules-based voting system to classify which regime we're currently in.

**How does it work?**
Each indicator "votes" for a regime based on its current value:
- **Expansion** 🟢 — Jobs growing, markets calm, consumers confident
- **Slowdown** 🟡 — Growth losing steam, some warning signs
- **Contraction** 🔴 — Economy shrinking, rising unemployment
- **Crisis** 🔴🔴 — Severe stress, market panic, credit freeze

**The confidence score** shows what percentage of indicators agree on the regime.
33% = mixed signals (uncertain). 80%+ = strong consensus.

**Why does this matter?** Different regimes favor different investment strategies.
Expansions favor stocks. Slowdowns favor bonds. Crises favor cash and gold.
        """)

    # ── Data fetch ────────────────────────────────────────────────────────
    test_date, test_val = cache.get_latest("UNRATE", "USA")
    has_data = test_val is not None

    if not has_data:
        st.markdown(
            glass_card(
                f'<div style="text-align:center;padding:20px">'
                f'<div style="font-size:2em;margin-bottom:8px">📊</div>'
                f'<div style="color:{TEXT_PRIMARY};font-size:1.1em;font-weight:600">'
                f'No Data Cached</div>'
                f'<div style="color:{TEXT_MUTED};font-size:0.85em;margin-top:6px">'
                f'Click below to fetch live FRED data for 30+ economic indicators from the Federal Reserve</div>'
                f'</div>',
                border_color="rgba(99,102,241,0.2)",
            ),
            unsafe_allow_html=True,
        )
        if st.button("📊 Fetch Live FRED Data", type="primary"):
            _do_fetch(get_fred_indicators, fred_client, cache)
            st.rerun()
        return

    # Refresh button
    col_title, col_refresh = st.columns([5, 1])
    with col_refresh:
        if st.button("🔄 Refresh"):
            _do_fetch(get_fred_indicators, fred_client, cache)
            st.rerun()

    # ── Gather all signal data ────────────────────────────────────────────
    signals: dict[str, dict] = {}

    for sid, meta in REGIME_SIGNALS.items():
        df = cache.get_observations(sid, country="USA")
        if df.empty:
            continue

        monthly = df["value"].resample("ME").last().dropna()
        if len(monthly) < 3:
            continue

        # Compute transformed latest value
        if sid in YOY_SERIES and len(monthly) >= 13:
            latest = (monthly.iloc[-1] / monthly.iloc[-13] - 1) * 100
            transform_series = (monthly / monthly.shift(12) - 1) * 100
            transform_series = transform_series.dropna()
        elif sid in MOM_SERIES and len(monthly) >= 2:
            latest = monthly.iloc[-1] - monthly.iloc[-2]
            transform_series = monthly.diff().dropna()
        elif sid in QOQ_SERIES and len(monthly) >= 4:
            latest = (monthly.iloc[-1] / monthly.iloc[-4] - 1) * 100
            transform_series = (monthly / monthly.shift(3) - 1) * 100
            transform_series = transform_series.dropna()
        else:
            latest = float(monthly.iloc[-1])
            transform_series = monthly

        z = _compute_z(transform_series)
        trend = _trend_direction(transform_series)
        date_str = str(monthly.index[-1].date())

        signals[sid] = {
            "latest": round(latest, 2),
            "z_score": z,
            "trend": trend,
            "date": date_str,
            "series": monthly,
            "transform_series": transform_series,
            **meta,
        }

    # ── Regime Classification ─────────────────────────────────────────────
    regime_name, regime_color, confidence, votes, rationale = _classify_regime(signals)
    regime_info = REGIME_EXPLANATIONS.get(regime_name, REGIME_EXPLANATIONS["Unknown"])

    # ── HERO: Regime card + gauge + vote breakdown ────────────────────────
    c1, c2, c3 = st.columns([2, 3, 2])

    with c1:
        st.markdown(
            glass_card(
                f'<div style="text-align:center;padding:12px">'
                f'<div style="color:{TEXT_MUTED};font-size:0.72em;text-transform:uppercase;'
                f'letter-spacing:1.2px;font-weight:600">Current Regime</div>'
                f'<div style="color:{regime_color};font-size:2.4em;font-weight:800;'
                f'margin:8px 0;letter-spacing:-0.5px">{regime_name}</div>'
                f'<div style="color:{TEXT_MUTED};font-size:0.85em">'
                f'Confidence: <span style="color:{regime_color};font-weight:700">'
                f'{confidence:.0%}</span></div>'
                f'</div>',
                border_color=f"{regime_color}44",
            ),
            unsafe_allow_html=True,
        )

    with c2:
        # Regime gauge chart
        gauge_val = confidence * 100 * (1 if regime_name == "Expansion" else -1 if regime_name in ("Contraction", "Crisis") else 0.3)
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=gauge_val,
            number=dict(suffix="%", font=dict(size=28, color=regime_color)),
            gauge=dict(
                axis=dict(range=[-100, 100], tickfont=dict(size=10, color="#64748b")),
                bar=dict(color=regime_color, thickness=0.3),
                bgcolor="rgba(255,255,255,0.02)",
                borderwidth=0,
                steps=[
                    dict(range=[-100, -25], color="rgba(239,68,68,0.15)"),
                    dict(range=[-25, 25], color="rgba(234,179,8,0.1)"),
                    dict(range=[25, 100], color="rgba(34,197,94,0.15)"),
                ],
                threshold=dict(line=dict(color=regime_color, width=3), thickness=0.8, value=gauge_val),
            ),
        ))
        fig.update_layout(
            height=200, margin=dict(l=30, r=30, t=30, b=10),
            paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c3:
        # Vote breakdown
        vote_html = ""
        for regime, count in sorted(votes.items(), key=lambda x: x[1], reverse=True):
            color = {"Expansion": GREEN, "Slowdown": YELLOW, "Contraction": RED, "Crisis": "#dc2626"}[regime]
            pct = count / max(sum(votes.values()), 1) * 100
            vote_html += (
                f'<div style="margin:6px 0;display:flex;align-items:center;gap:8px">'
                f'<div style="color:{color};font-weight:600;font-size:0.85em;width:90px">{regime}</div>'
                f'<div style="flex:1;background:rgba(255,255,255,0.05);border-radius:6px;height:18px;overflow:hidden">'
                f'<div style="width:{pct}%;height:100%;background:{color};border-radius:6px;'
                f'transition:width 0.3s"></div></div>'
                f'<div style="color:{TEXT_MUTED};font-size:0.78em;width:30px;text-align:right">{count}</div>'
                f'</div>'
            )
        st.markdown(
            glass_card(
                f'<div style="color:{TEXT_MUTED};font-size:0.72em;text-transform:uppercase;'
                f'letter-spacing:1.2px;font-weight:600;margin-bottom:8px">Signal Votes</div>'
                f'{vote_html}',
            ),
            unsafe_allow_html=True,
        )

    # ── Regime Interpretation (plain English) ─────────────────────────────
    st.markdown(
        glass_card(
            f'<div style="display:flex;gap:24px;flex-wrap:wrap">'
            f'<div style="flex:1;min-width:280px">'
            f'<div style="color:{regime_color};font-weight:700;font-size:1.1em;margin-bottom:6px">'
            f'📋 What does "{regime_name}" mean?</div>'
            f'<div style="color:{TEXT_PRIMARY};font-size:0.92em;line-height:1.6;margin-bottom:10px">'
            f'{regime_info["detail"]}</div>'
            f'</div>'
            f'<div style="flex:1;min-width:280px">'
            f'<div style="color:{YELLOW};font-weight:700;font-size:0.92em;margin-bottom:6px">'
            f'👀 What to Watch</div>'
            f'<div style="color:{TEXT_SECONDARY};font-size:0.88em;line-height:1.5;margin-bottom:10px">'
            f'{regime_info["what_to_watch"]}</div>'
            f'<div style="color:{TEXT_DIM};font-weight:700;font-size:0.82em;margin-bottom:4px">'
            f'📚 Historical Context</div>'
            f'<div style="color:{TEXT_DIM};font-size:0.82em;line-height:1.5">'
            f'{regime_info["historical"]}</div>'
            f'</div>'
            f'</div>',
            border_color=f"{regime_color}33",
        ),
        unsafe_allow_html=True,
    )

    # ── Why the model voted this way (show all rationale) ─────────────────
    if rationale:
        # Group rationale by regime
        rationale_by_regime: dict[str, list[str]] = {}
        for r in rationale:
            # Figure out which regime this rationale supported
            for regime_key in ["Expansion", "Slowdown", "Contraction", "Crisis"]:
                # The rationale was added by _vote which incremented a specific regime
                pass
        # Simple approach: just show all reasoning
        expansion_reasons = [r for i, r in enumerate(rationale) if i < len(rationale)]

        st.markdown(section_header("Why Each Indicator Voted This Way"), unsafe_allow_html=True)
        st.markdown(
            f'<div style="color:{TEXT_DIM};font-size:0.82em;margin:-8px 0 12px 0">'
            f'The regime classification is based on {len(rationale)} individual signal votes. '
            f'Each indicator evaluates BOTH its current level AND its momentum/trend to cast a vote.</div>',
            unsafe_allow_html=True,
        )

        # Build colored rationale list
        rationale_html = ""
        # We need to know which regime each rationale voted for
        # Re-run the classification logic just to get the mapping
        vote_mapping = _get_vote_mapping(signals)

        for regime_voted, reason in vote_mapping:
            color = {"Expansion": GREEN, "Slowdown": YELLOW, "Contraction": RED, "Crisis": "#dc2626"}.get(regime_voted, GRAY)
            icon = {"Expansion": "🟢", "Slowdown": "🟡", "Contraction": "🔴", "Crisis": "🔴"}.get(regime_voted, "⚪")
            rationale_html += (
                f'<div style="display:flex;align-items:flex-start;gap:8px;padding:5px 0;'
                f'border-bottom:1px solid rgba(255,255,255,0.04)">'
                f'<span style="font-size:0.8em;flex-shrink:0">{icon}</span>'
                f'<span style="color:{TEXT_SECONDARY};font-size:0.85em;flex:1">{reason}</span>'
                f'<span style="color:{color};font-size:0.72em;font-weight:600;flex-shrink:0;'
                f'padding:2px 6px;background:rgba(255,255,255,0.04);border-radius:4px">'
                f'{regime_voted}</span>'
                f'</div>'
            )

        st.markdown(
            glass_card(rationale_html, border_color="rgba(255,255,255,0.06)"),
            unsafe_allow_html=True,
        )

    st.markdown("", unsafe_allow_html=True)

    # ── SIGNIFICANT MOVERS ────────────────────────────────────────────────
    st.markdown(section_header("Significant Movers — Indicators That Stand Out Right Now"), unsafe_allow_html=True)
    st.markdown(
        f'<div style="color:{TEXT_DIM};font-size:0.82em;margin:-8px 0 12px 0">'
        f'These indicators have moved significantly from their 5-year average. '
        f'Larger Z-scores mean more unusual readings. Hover any card for a plain-English explanation.</div>',
        unsafe_allow_html=True,
    )

    movers = [
        (sid, data) for sid, data in signals.items()
        if data.get("z_score") is not None and abs(data["z_score"]) > 0.5
    ]
    movers.sort(key=lambda x: abs(x[1]["z_score"]), reverse=True)

    if movers:
        cols = st.columns(min(4, len(movers)))
        for i, (sid, data) in enumerate(movers[:8]):
            with cols[i % min(4, len(movers))]:
                z = data["z_score"]
                zc = z_color(z)
                cat_color = CATEGORY_COLORS.get(data["cat"], GRAY)
                tc = trend_color(data["trend"], data["higher_is"])
                ta = trend_arrow(data["trend"], data["higher_is"])

                az = abs(z)
                if az >= 2.5:
                    mag = "EXTREME"
                    mag_explain = "Extremely rare reading"
                elif az >= 1.5:
                    mag = "HIGH"
                    mag_explain = "Notably unusual"
                else:
                    mag = "MODERATE"
                    mag_explain = "Somewhat elevated"

                # Build a plain-english explanation of the reading
                explain = data.get("explain", "")

                st.markdown(
                    f'<div style="background:linear-gradient(135deg,rgba(255,255,255,0.04),rgba(255,255,255,0.015));'
                    f'border:1px solid rgba(255,255,255,0.08);border-left:4px solid {zc};'
                    f'border-radius:0 12px 12px 0;padding:14px 16px;margin-bottom:8px" '
                    f'title="{explain}">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
                    f'{badge(data["cat"], cat_color)}'
                    f'{badge(mag, zc)}'
                    f'</div>'
                    f'<div style="color:{TEXT_PRIMARY};font-weight:600;font-size:0.9em;margin:4px 0">'
                    f'{data["label"]}</div>'
                    f'<div style="display:flex;justify-content:space-between;align-items:baseline">'
                    f'<span style="color:{tc};font-size:1.4em;font-weight:700">'
                    f'{ta} {data["latest"]:.2f}</span>'
                    f'<span style="color:{zc};font-size:0.82em;font-weight:600">'
                    f'{z:+.2f}σ</span>'
                    f'</div>'
                    f'<div style="color:{TEXT_DIM};font-size:0.68em;margin-top:4px">{data["date"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("No significant movers detected — all indicators are near their historical averages.")

    # ── INDICATOR DEEP-DIVE BY CATEGORY ───────────────────────────────────
    st.markdown(section_header("All Indicators by Category"), unsafe_allow_html=True)
    st.markdown(
        f'<div style="color:{TEXT_DIM};font-size:0.82em;margin:-8px 0 12px 0">'
        f'Click any category tab to see its indicators. Each card shows the latest value, '
        f'its Z-score (how unusual it is), and its recent trend direction.</div>',
        unsafe_allow_html=True,
    )

    by_cat: dict[str, list] = {}
    for sid, data in signals.items():
        by_cat.setdefault(data["cat"], []).append((sid, data))

    cat_order = ["Inflation", "Labor", "Output", "Consumer", "Monetary", "Fixed Income", "Market", "Housing"]
    available_cats = [c for c in cat_order if c in by_cat]

    # Category descriptions for laymen
    cat_descriptions = {
        "Inflation": "Are prices rising too fast? The Fed wants 2% inflation. Much higher squeezes consumers and triggers rate hikes.",
        "Labor": "Is the job market strong or weakening? Jobs are the backbone of consumer spending, which drives 70% of GDP.",
        "Output": "How much is the economy actually producing? GDP, factory output, and capacity usage measure real economic activity.",
        "Consumer": "How do people feel and what are they buying? Consumer spending is the largest component of the US economy.",
        "Monetary": "What is the Federal Reserve doing? Interest rates and money supply are the Fed's main tools to control the economy.",
        "Fixed Income": "What are bond markets telling us? The yield curve and credit spreads are powerful predictors of recessions.",
        "Market": "How scared or calm are investors? Market volatility and the dollar reflect global risk appetite.",
        "Housing": "Is the housing market healthy? Housing is a leading indicator — it turns down before recessions start.",
    }

    tabs = st.tabs(available_cats)

    for tab, cat_name in zip(tabs, available_cats):
        with tab:
            # Category explanation
            st.markdown(
                f'<div style="color:{TEXT_SECONDARY};font-size:0.88em;margin-bottom:14px;'
                f'padding:10px 14px;background:rgba(255,255,255,0.02);border-radius:8px;'
                f'border-left:3px solid {CATEGORY_COLORS.get(cat_name, GRAY)}">'
                f'{cat_descriptions.get(cat_name, "")}</div>',
                unsafe_allow_html=True,
            )

            items = by_cat[cat_name]
            for sid, data in items:
                z = data.get("z_score")
                tc = trend_color(data["trend"], data["higher_is"])
                ta = trend_arrow(data["trend"], data["higher_is"])
                explain = data.get("explain", "")

                col_metric, col_explain = st.columns([1, 2])

                with col_metric:
                    st.metric(
                        data["label"],
                        f"{data['latest']:.2f}",
                        delta=f"{ta} {z:+.1f}σ" if z is not None else None,
                    )
                    bar_color = z_color(z) if z is not None else GRAY
                    st.markdown(
                        f'<div style="height:3px;background:{bar_color};border-radius:2px;'
                        f'margin:-8px 0 8px 0;opacity:0.7"></div>',
                        unsafe_allow_html=True,
                    )

                with col_explain:
                    # Plain-English explanation
                    trend_word = {
                        "improving": "trending in a healthy direction",
                        "deteriorating": "trending in a concerning direction",
                        "stable": "holding steady",
                    }.get(data["trend"], "stable")

                    st.markdown(
                        f'<div style="color:{TEXT_SECONDARY};font-size:0.85em;line-height:1.5;'
                        f'padding-top:8px">{explain}</div>'
                        f'<div style="color:{TEXT_DIM};font-size:0.78em;margin-top:4px">'
                        f'📈 Currently <b style="color:{tc}">{trend_word}</b> · '
                        f'Updated: {data["date"]}</div>',
                        unsafe_allow_html=True,
                    )

    # ── Z-SCORE OVERVIEW ──────────────────────────────────────────────────
    st.markdown(section_header("Z-Score Overview — How Unusual Are Current Readings?"), unsafe_allow_html=True)
    st.markdown(
        f'<div style="color:{TEXT_DIM};font-size:0.82em;margin:-8px 0 12px 0">{ZSCORE_EXPLAIN}</div>',
        unsafe_allow_html=True,
    )

    z_data = [
        (data["label"], data["z_score"])
        for data in signals.values()
        if data.get("z_score") is not None
    ]
    z_data.sort(key=lambda x: x[1])

    if z_data:
        labels, values = zip(*z_data)

        fig = go.Figure(go.Bar(
            x=list(values),
            y=list(labels),
            orientation="h",
            marker=dict(color=[z_color(v) for v in values]),
            text=[f"{v:+.2f}" for v in values],
            textposition="outside",
            textfont=dict(size=11, color="#e2e8f0"),
        ))
        fig.update_layout(
            height=max(400, len(labels) * 32),
            xaxis_title="Z-Score (how many standard deviations from normal)",
            yaxis=dict(autorange="reversed", tickfont=dict(size=11, color="#94a3b8")),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color="#94a3b8"),
            margin=dict(l=20, r=80, t=10, b=40),
            xaxis=dict(gridcolor="rgba(255,255,255,0.04)", zeroline=True,
                       zerolinecolor="rgba(255,255,255,0.15)", zerolinewidth=1),
        )
        fig.add_vline(x=-2, line_dash="dash", line_color="#ef4444", opacity=0.4,
                      annotation_text="Unusually low ←", annotation_font_color="#ef4444",
                      annotation_font_size=10)
        fig.add_vline(x=2, line_dash="dash", line_color="#ef4444", opacity=0.4,
                      annotation_text="→ Unusually high", annotation_font_color="#ef4444",
                      annotation_font_size=10)
        st.plotly_chart(fig, use_container_width=True)

    # ── SPARKLINE TRENDS ──────────────────────────────────────────────────
    st.markdown(section_header("Key Indicators — 3-Year Trend Lines"), unsafe_allow_html=True)
    st.markdown(
        f'<div style="color:{TEXT_DIM};font-size:0.82em;margin:-8px 0 12px 0">'
        f'Each mini-chart shows how an indicator has moved over the past 3 years. '
        f'Look for trends: steady climbs, sharp drops, or reversals.</div>',
        unsafe_allow_html=True,
    )

    spark_ids = ["UNRATE", "CPIAUCSL", "T10Y2Y", "VIXCLS", "FEDFUNDS", "INDPRO",
                 "BAMLH0A0HYM2", "UMCSENT", "ICSA"]
    spark_cols = st.columns(3)

    for i, sid in enumerate(spark_ids):
        if sid not in signals:
            continue
        data = signals[sid]
        series = data.get("transform_series", data["series"])
        series = series.tail(36)
        if len(series) < 3:
            continue

        with spark_cols[i % 3]:
            fig = go.Figure(go.Scatter(
                x=series.index, y=series.values,
                mode="lines", fill="tozeroy",
                line=dict(color="#818cf8", width=1.5),
                fillcolor="rgba(129,140,248,0.08)",
            ))
            fig.update_layout(
                height=130,
                margin=dict(l=0, r=0, t=28, b=0),
                title=dict(
                    text=f"{data['label']}: <b>{data['latest']:.2f}</b>",
                    font=dict(size=11, color="#e2e8f0"),
                ),
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, key=f"spark_{sid}")

    # ── CORRELATION HEATMAP ───────────────────────────────────────────────
    with st.expander("🔗 Indicator Cross-Correlations (Advanced)", expanded=False):
        st.markdown(
            f'<div style="color:{TEXT_SECONDARY};font-size:0.88em;margin-bottom:12px">'
            f'This matrix shows how indicators move together over the past 36 months. '
            f'<b>Blue = move together</b> (positive correlation). '
            f'<b>Red = move opposite</b> (negative correlation). '
            f'Strong correlations (±0.7+) reveal hidden economic linkages.</div>',
            unsafe_allow_html=True,
        )

        from macro_intel.analytics.correlations import build_indicator_correlation_matrix
        corr = build_indicator_correlation_matrix(
            series_ids=list(REGIME_SIGNALS.keys()),
            country="USA", lookback_months=36,
        )
        if not corr.empty:
            rename_map = {sid: REGIME_SIGNALS[sid]["label"] for sid in corr.columns if sid in REGIME_SIGNALS}
            corr = corr.rename(index=rename_map, columns=rename_map)

            fig = go.Figure(go.Heatmap(
                z=corr.values, x=corr.columns.tolist(), y=corr.index.tolist(),
                colorscale="RdBu_r", zmid=0, zmin=-1, zmax=1,
                text=corr.round(2).values, texttemplate="%{text}",
                textfont=dict(size=9),
            ))
            fig.update_layout(
                height=max(500, len(corr) * 30),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter", color="#94a3b8"),
                margin=dict(l=20, r=20, t=10, b=10),
                xaxis=dict(tickangle=45, tickfont=dict(size=9)),
                yaxis=dict(tickfont=dict(size=9)),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data to compute correlations. Try refreshing the data.")


def _do_fetch(get_fred_indicators, fred_client, cache):
    """Fetch all FRED indicators into cache."""
    fred_ids = list(get_fred_indicators().keys())
    progress = st.progress(0, text="Fetching FRED data...")
    fetched = 0
    for i, sid in enumerate(fred_ids):
        try:
            df = fred_client.fetch_series(sid, lookback_years=10)
            if not df.empty:
                cache.upsert_observations(sid, df, country="USA")
                fetched += 1
        except Exception:
            pass
        progress.progress((i + 1) / len(fred_ids), text=f"Fetching {sid}... ({i+1}/{len(fred_ids)})")
    progress.empty()
    st.success(f"Fetched {fetched}/{len(fred_ids)} indicators")
