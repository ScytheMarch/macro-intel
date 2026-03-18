"""Regime Dashboard — live macro regime analysis with inline data fetching."""

from __future__ import annotations

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ── Lightweight regime classifier (no PyMC needed) ────────────────────────────

_REGIME_INDICATORS = {
    "UNRATE":       {"label": "Unemployment Rate",      "regime_thresholds": (4.0, 5.5, 7.0)},
    "CPIAUCSL":     {"label": "CPI YoY %",              "regime_thresholds": (2.0, 3.5, 5.0)},
    "T10Y2Y":       {"label": "Yield Curve (10Y-2Y)",   "regime_thresholds": (0.5, 0.0, -0.5)},
    "FEDFUNDS":     {"label": "Fed Funds Rate",         "regime_thresholds": (2.0, 4.0, 5.5)},
    "INDPRO":       {"label": "Industrial Production",  "regime_thresholds": None},
    "VIXCLS":       {"label": "VIX",                    "regime_thresholds": (15, 20, 30)},
    "BAMLH0A0HYM2": {"label": "HY Credit Spread",      "regime_thresholds": (3.5, 5.0, 7.0)},
    "UMCSENT":      {"label": "Consumer Sentiment",     "regime_thresholds": None},
    "ICSA":         {"label": "Initial Claims (K)",     "regime_thresholds": (220, 280, 350)},
    "PAYEMS":       {"label": "Nonfarm Payrolls",       "regime_thresholds": None},
}


def _classify_regime(indicators: dict[str, float]) -> tuple[str, str, float]:
    """Rules-based regime classification from latest indicator values.

    Returns (regime_name, color, confidence).
    """
    signals = {"expansion": 0, "slowdown": 0, "contraction": 0, "crisis": 0}
    total = 0

    ur = indicators.get("UNRATE")
    if ur is not None:
        total += 1
        if ur < 4.5:
            signals["expansion"] += 1
        elif ur < 6.0:
            signals["slowdown"] += 1
        else:
            signals["contraction"] += 1

    yc = indicators.get("T10Y2Y")
    if yc is not None:
        total += 1
        if yc > 0.5:
            signals["expansion"] += 1
        elif yc > 0:
            signals["slowdown"] += 1
        elif yc > -0.5:
            signals["contraction"] += 1
        else:
            signals["crisis"] += 1

    vix = indicators.get("VIXCLS")
    if vix is not None:
        total += 1
        if vix < 18:
            signals["expansion"] += 1
        elif vix < 25:
            signals["slowdown"] += 1
        elif vix < 35:
            signals["contraction"] += 1
        else:
            signals["crisis"] += 1

    hy = indicators.get("BAMLH0A0HYM2")
    if hy is not None:
        total += 1
        if hy < 4.0:
            signals["expansion"] += 1
        elif hy < 5.5:
            signals["slowdown"] += 1
        elif hy < 8.0:
            signals["contraction"] += 1
        else:
            signals["crisis"] += 1

    claims = indicators.get("ICSA")
    if claims is not None:
        total += 1
        if claims < 230:
            signals["expansion"] += 1
        elif claims < 300:
            signals["slowdown"] += 1
        elif claims < 400:
            signals["contraction"] += 1
        else:
            signals["crisis"] += 1

    sent = indicators.get("UMCSENT")
    if sent is not None:
        total += 1
        if sent > 80:
            signals["expansion"] += 1
        elif sent > 65:
            signals["slowdown"] += 1
        elif sent > 50:
            signals["contraction"] += 1
        else:
            signals["crisis"] += 1

    if total == 0:
        return "Unknown", "#6b7280", 0.0

    regime = max(signals, key=signals.get)
    confidence = signals[regime] / total

    colors = {
        "expansion": "#22c55e",
        "slowdown": "#f59e0b",
        "contraction": "#ef4444",
        "crisis": "#dc2626",
    }
    return regime.title(), colors[regime], confidence


def _compute_z_score(series: pd.Series, window: int = 60) -> float | None:
    """Compute z-score of latest value vs trailing window."""
    if len(series) < window:
        if len(series) < 12:
            return None
        window = len(series)
    recent = series.tail(window)
    mean = recent.mean()
    std = recent.std()
    if std == 0 or pd.isna(std):
        return None
    return float((series.iloc[-1] - mean) / std)


def render():
    st.markdown(
        '<h2>🧠 <span style="background:linear-gradient(135deg,#818cf8,#a78bfa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent">'
        'Regime Dashboard</span></h2>',
        unsafe_allow_html=True,
    )

    from macro_intel.config.indicators import get_fred_indicators, REGIME_FEATURES
    from macro_intel.data import cache, fred_client

    # ── Check if we have data, offer to fetch ─────────────────────────────
    test_date, test_val = cache.get_latest("UNRATE", "USA")
    has_data = test_val is not None

    if not has_data:
        st.info("No cached data found. Click below to fetch live macro data from FRED.")

    col_fetch, col_status = st.columns([1, 3])
    with col_fetch:
        fetch_clicked = st.button(
            "🔄 Fetch Live Data" if has_data else "📊 Fetch Data Now",
            type="primary" if not has_data else "secondary",
        )

    if fetch_clicked:
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
            progress.progress((i + 1) / len(fred_ids),
                              text=f"Fetching {sid}... ({i+1}/{len(fred_ids)})")
        progress.empty()
        st.success(f"Fetched {fetched}/{len(fred_ids)} FRED indicators")
        st.rerun()

    if not has_data and not fetch_clicked:
        return

    # ── Gather latest values ──────────────────────────────────────────────
    latest_values: dict[str, float] = {}
    series_data: dict[str, pd.DataFrame] = {}

    for sid in _REGIME_INDICATORS:
        df = cache.get_observations(sid, country="USA")
        if not df.empty:
            latest_values[sid] = float(df["value"].iloc[-1])
            series_data[sid] = df

    # For CPI, compute YoY % change
    cpi_df = cache.get_observations("CPIAUCSL", country="USA")
    if not cpi_df.empty and len(cpi_df) >= 13:
        cpi_yoy = (cpi_df["value"].iloc[-1] / cpi_df["value"].iloc[-13] - 1) * 100
        latest_values["CPIAUCSL"] = round(cpi_yoy, 2)

    # For Payrolls, compute month-over-month change
    payrolls_df = cache.get_observations("PAYEMS", country="USA")
    if not payrolls_df.empty and len(payrolls_df) >= 2:
        mom = payrolls_df["value"].iloc[-1] - payrolls_df["value"].iloc[-2]
        latest_values["PAYEMS"] = round(mom, 1)

    # For Industrial Production, compute YoY %
    indpro_df = cache.get_observations("INDPRO", country="USA")
    if not indpro_df.empty and len(indpro_df) >= 13:
        indpro_yoy = (indpro_df["value"].iloc[-1] / indpro_df["value"].iloc[-13] - 1) * 100
        latest_values["INDPRO"] = round(indpro_yoy, 2)

    # ── Regime Classification ─────────────────────────────────────────────
    regime_name, regime_color, confidence = _classify_regime(latest_values)

    # Header cards
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div style="background:{regime_color}22;border:2px solid {regime_color};'
            f'border-radius:12px;padding:20px;text-align:center">'
            f'<p style="color:#94a3b8;margin:0;font-size:0.85em">Current Regime</p>'
            f'<h1 style="color:{regime_color};margin:8px 0">{regime_name}</h1>'
            f'<p style="color:#94a3b8;margin:0">Confidence: {confidence:.0%}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c2:
        # Signal breakdown
        st.markdown("**Signal Breakdown**")
        for sid, info in _REGIME_INDICATORS.items():
            val = latest_values.get(sid)
            if val is not None:
                st.text(f"{info['label']:.<30s} {val:>8.2f}")
    with c3:
        # Data freshness
        st.markdown("**Data Freshness**")
        for sid in ["UNRATE", "CPIAUCSL", "FEDFUNDS", "T10Y2Y", "VIXCLS"]:
            date_str, _ = cache.get_latest(sid, "USA")
            label = _REGIME_INDICATORS.get(sid, {}).get("label", sid)
            if date_str:
                st.text(f"{label:.<25s} {date_str}")

    st.divider()

    # ── Z-Score Heatmap ───────────────────────────────────────────────────
    st.subheader("Macro Z-Scores (vs 5yr history)")

    z_scores: dict[str, float] = {}
    for sid in _REGIME_INDICATORS:
        df = cache.get_observations(sid, country="USA")
        if not df.empty:
            monthly = df["value"].resample("ME").last().dropna()
            z = _compute_z_score(monthly)
            if z is not None:
                z_scores[_REGIME_INDICATORS[sid]["label"]] = z

    if z_scores:
        labels = list(z_scores.keys())
        values = list(z_scores.values())

        fig = go.Figure(go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker=dict(
                color=[
                    "#22c55e" if abs(v) < 1 else "#f59e0b" if abs(v) < 2 else "#ef4444"
                    for v in values
                ],
            ),
            text=[f"{v:+.2f}" for v in values],
            textposition="outside",
        ))
        fig.update_layout(
            height=max(350, len(labels) * 35),
            xaxis_title="Z-Score",
            yaxis=dict(autorange="reversed"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            margin=dict(l=20, r=60, t=20, b=40),
        )
        fig.add_vline(x=-2, line_dash="dash", line_color="#ef4444", opacity=0.5)
        fig.add_vline(x=2, line_dash="dash", line_color="#ef4444", opacity=0.5)
        fig.add_vline(x=0, line_color="#64748b", opacity=0.5)
        st.plotly_chart(fig, use_container_width=True)

    # ── Key Indicator Sparklines ──────────────────────────────────────────
    st.subheader("Key Indicators (3yr Trend)")

    spark_indicators = ["UNRATE", "CPIAUCSL", "T10Y2Y", "VIXCLS", "FEDFUNDS", "INDPRO"]
    cols = st.columns(3)
    for i, sid in enumerate(spark_indicators):
        df = cache.get_observations(sid, country="USA")
        if df.empty:
            continue
        monthly = df["value"].resample("ME").last().dropna().tail(36)
        if len(monthly) < 3:
            continue

        with cols[i % 3]:
            label = _REGIME_INDICATORS.get(sid, {}).get("label", sid)
            latest = monthly.iloc[-1]
            prev = monthly.iloc[-2]
            delta = latest - prev

            fig = go.Figure(go.Scatter(
                x=monthly.index,
                y=monthly.values,
                mode="lines",
                fill="tozeroy",
                line=dict(color="#818cf8", width=2),
                fillcolor="rgba(129,140,248,0.15)",
            ))
            fig.update_layout(
                height=160,
                margin=dict(l=0, r=0, t=30, b=0),
                title=dict(text=f"{label}: {latest:.2f}", font=dict(size=13, color="#e2e8f0")),
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, key=f"spark_{sid}")

    # ── Correlation Snapshot ──────────────────────────────────────────────
    st.subheader("Indicator Correlations (36mo)")

    from macro_intel.analytics.correlations import build_indicator_correlation_matrix
    corr = build_indicator_correlation_matrix(
        series_ids=list(_REGIME_INDICATORS.keys()),
        country="USA",
        lookback_months=36,
    )
    if not corr.empty:
        # Rename columns for readability
        rename_map = {sid: info["label"] for sid, info in _REGIME_INDICATORS.items()}
        corr = corr.rename(index=rename_map, columns=rename_map)

        fig = go.Figure(go.Heatmap(
            z=corr.values,
            x=corr.columns.tolist(),
            y=corr.index.tolist(),
            colorscale="RdBu_r",
            zmid=0,
            zmin=-1,
            zmax=1,
            text=corr.round(2).values,
            texttemplate="%{text}",
            textfont=dict(size=10),
        ))
        fig.update_layout(
            height=500,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis=dict(tickangle=45),
        )
        st.plotly_chart(fig, use_container_width=True)
