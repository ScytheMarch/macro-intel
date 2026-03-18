"""Regime Dashboard — real-time macro regime monitoring with traffic-light signals."""

from __future__ import annotations

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ── Indicator metadata for regime signals ─────────────────────────────────────

REGIME_SIGNALS = {
    "UNRATE":       {"label": "Unemployment Rate",      "cat": "Labor",        "unit": "percent",   "higher_is": "contractionary"},
    "CPIAUCSL":     {"label": "CPI YoY",                "cat": "Inflation",    "unit": "percent",   "higher_is": "inflationary"},
    "CPILFESL":     {"label": "Core CPI YoY",           "cat": "Inflation",    "unit": "percent",   "higher_is": "inflationary"},
    "PAYEMS":       {"label": "Nonfarm Payrolls MoM",   "cat": "Labor",        "unit": "thousands", "higher_is": "expansionary"},
    "ICSA":         {"label": "Initial Claims",         "cat": "Labor",        "unit": "thousands", "higher_is": "contractionary"},
    "T10Y2Y":       {"label": "Yield Curve 10Y-2Y",     "cat": "Fixed Income", "unit": "percent",   "higher_is": "expansionary"},
    "FEDFUNDS":     {"label": "Fed Funds Rate",         "cat": "Monetary",     "unit": "percent",   "higher_is": "contractionary"},
    "VIXCLS":       {"label": "VIX",                    "cat": "Market",       "unit": "index",     "higher_is": "contractionary"},
    "BAMLH0A0HYM2": {"label": "HY Credit Spread",      "cat": "Fixed Income", "unit": "percent",   "higher_is": "contractionary"},
    "UMCSENT":      {"label": "Consumer Sentiment",     "cat": "Consumer",     "unit": "index",     "higher_is": "expansionary"},
    "INDPRO":       {"label": "Industrial Prod YoY",    "cat": "Output",       "unit": "percent",   "higher_is": "expansionary"},
    "RSAFS":        {"label": "Retail Sales MoM",       "cat": "Consumer",     "unit": "percent",   "higher_is": "expansionary"},
    "GDPC1":        {"label": "Real GDP QoQ",           "cat": "Output",       "unit": "percent",   "higher_is": "expansionary"},
    "DGS10":        {"label": "10Y Treasury Yield",     "cat": "Fixed Income", "unit": "percent",   "higher_is": "neutral"},
    "DGS2":         {"label": "2Y Treasury Yield",      "cat": "Fixed Income", "unit": "percent",   "higher_is": "neutral"},
    "M2SL":         {"label": "M2 Money Supply YoY",    "cat": "Monetary",     "unit": "percent",   "higher_is": "inflationary"},
    "HOUST":        {"label": "Housing Starts",         "cat": "Housing",      "unit": "thousands", "higher_is": "expansionary"},
    "TCU":          {"label": "Capacity Utilization",   "cat": "Output",       "unit": "percent",   "higher_is": "expansionary"},
    "PSAVERT":      {"label": "Personal Saving Rate",   "cat": "Consumer",     "unit": "percent",   "higher_is": "neutral"},
}

# Which series need YoY transforms
YOY_SERIES = {"CPIAUCSL", "CPILFESL", "INDPRO", "M2SL"}
MOM_SERIES = {"PAYEMS", "RSAFS"}
QOQ_SERIES = {"GDPC1"}


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
    slope = np.polyfit(range(len(recent)), recent.values, 1)[0]
    if slope > 0.01 * recent.std():
        return "improving"
    elif slope < -0.01 * recent.std():
        return "deteriorating"
    return "stable"


def _classify_regime(signals: dict[str, dict]) -> tuple[str, str, float, dict[str, int]]:
    """Rules-based regime from latest indicators. Returns (name, color, confidence, vote_counts)."""
    votes = {"Expansion": 0, "Slowdown": 0, "Contraction": 0, "Crisis": 0}
    total = 0

    for sid, data in signals.items():
        val = data.get("latest")
        if val is None:
            continue

        if sid == "UNRATE":
            total += 1
            if val < 4.5: votes["Expansion"] += 1
            elif val < 6.0: votes["Slowdown"] += 1
            else: votes["Contraction"] += 1
        elif sid == "T10Y2Y":
            total += 1
            if val > 0.5: votes["Expansion"] += 1
            elif val > 0: votes["Slowdown"] += 1
            elif val > -0.5: votes["Contraction"] += 1
            else: votes["Crisis"] += 1
        elif sid == "VIXCLS":
            total += 1
            if val < 18: votes["Expansion"] += 1
            elif val < 25: votes["Slowdown"] += 1
            elif val < 35: votes["Contraction"] += 1
            else: votes["Crisis"] += 1
        elif sid == "BAMLH0A0HYM2":
            total += 1
            if val < 4.0: votes["Expansion"] += 1
            elif val < 5.5: votes["Slowdown"] += 1
            elif val < 8.0: votes["Contraction"] += 1
            else: votes["Crisis"] += 1
        elif sid == "ICSA":
            total += 1
            if val < 230: votes["Expansion"] += 1
            elif val < 300: votes["Slowdown"] += 1
            elif val < 400: votes["Contraction"] += 1
            else: votes["Crisis"] += 1
        elif sid == "UMCSENT":
            total += 1
            if val > 80: votes["Expansion"] += 1
            elif val > 65: votes["Slowdown"] += 1
            elif val > 50: votes["Contraction"] += 1
            else: votes["Crisis"] += 1

    if total == 0:
        return "Unknown", "#6b7280", 0.0, votes

    regime = max(votes, key=votes.get)
    confidence = votes[regime] / total
    colors = {"Expansion": "#22c55e", "Slowdown": "#eab308", "Contraction": "#ef4444", "Crisis": "#dc2626"}
    return regime, colors[regime], confidence, votes


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
        f'margin-bottom:16px">Real-time macro regime classification · '
        f'Rules-based signal aggregation</div>',
        unsafe_allow_html=True,
    )

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
                f'Click below to fetch live FRED data for 30+ economic indicators</div>'
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
    regime_name, regime_color, confidence, votes = _classify_regime(signals)

    # ── HERO: Regime gauge + vote breakdown ───────────────────────────────
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
                border_color=regime_color.replace(")", ",0.3)").replace("rgb", "rgba") if "rgb" in regime_color else f"{regime_color}44",
            ),
            unsafe_allow_html=True,
        )

    with c2:
        # Regime gauge chart
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=confidence * 100 * (1 if regime_name in ("Expansion",) else -1 if regime_name in ("Contraction", "Crisis") else 0.3),
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
                threshold=dict(line=dict(color=regime_color, width=3), thickness=0.8,
                               value=confidence * 100 * (1 if regime_name in ("Expansion",) else -1 if regime_name in ("Contraction", "Crisis") else 0.3)),
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

    st.markdown("", unsafe_allow_html=True)  # spacer

    # ── SIGNIFICANT MOVERS (sorted by |z-score|) ─────────────────────────
    st.markdown(section_header("Significant Movers"), unsafe_allow_html=True)

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

                # Magnitude label
                az = abs(z)
                if az >= 2.5:
                    mag = "EXTREME"
                elif az >= 1.5:
                    mag = "HIGH"
                else:
                    mag = "MODERATE"

                st.markdown(
                    f'<div style="background:linear-gradient(135deg,rgba(255,255,255,0.04),rgba(255,255,255,0.015));'
                    f'border:1px solid rgba(255,255,255,0.08);border-left:4px solid {zc};'
                    f'border-radius:0 12px 12px 0;padding:14px 16px;margin-bottom:8px">'
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

    # ── TRAFFIC-LIGHT GRID BY CATEGORY ────────────────────────────────────
    st.markdown(section_header("All Indicators by Category"), unsafe_allow_html=True)

    # Group by category
    by_cat: dict[str, list] = {}
    for sid, data in signals.items():
        by_cat.setdefault(data["cat"], []).append((sid, data))

    cat_order = ["Inflation", "Labor", "Output", "Consumer", "Monetary", "Fixed Income", "Market", "Housing"]
    tabs = st.tabs([c for c in cat_order if c in by_cat])

    for tab, cat_name in zip(tabs, [c for c in cat_order if c in by_cat]):
        with tab:
            items = by_cat[cat_name]
            cols = st.columns(min(4, len(items)))
            for i, (sid, data) in enumerate(items):
                with cols[i % min(4, len(items))]:
                    z = data.get("z_score")
                    tc = trend_color(data["trend"], data["higher_is"])
                    ta = trend_arrow(data["trend"], data["higher_is"])

                    st.metric(
                        data["label"],
                        f"{data['latest']:.2f}",
                        delta=f"{ta} {z:+.1f}σ" if z is not None else None,
                    )

                    # Color bar under metric
                    bar_color = z_color(z) if z is not None else GRAY
                    st.markdown(
                        f'<div style="height:3px;background:{bar_color};border-radius:2px;'
                        f'margin:-8px 0 8px 0;opacity:0.7"></div>',
                        unsafe_allow_html=True,
                    )

    # ── Z-SCORE BAR CHART ─────────────────────────────────────────────────
    st.markdown(section_header("Z-Score Overview (5yr baseline)"), unsafe_allow_html=True)

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
            xaxis_title="Z-Score (σ)",
            yaxis=dict(autorange="reversed", tickfont=dict(size=11, color="#94a3b8")),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color="#94a3b8"),
            margin=dict(l=20, r=80, t=10, b=40),
            xaxis=dict(gridcolor="rgba(255,255,255,0.04)", zeroline=True,
                       zerolinecolor="rgba(255,255,255,0.15)", zerolinewidth=1),
        )
        fig.add_vline(x=-2, line_dash="dash", line_color="#ef4444", opacity=0.4,
                      annotation_text="-2σ", annotation_font_color="#ef4444")
        fig.add_vline(x=2, line_dash="dash", line_color="#ef4444", opacity=0.4,
                      annotation_text="+2σ", annotation_font_color="#ef4444")
        st.plotly_chart(fig, use_container_width=True)

    # ── SPARKLINE GRID ────────────────────────────────────────────────────
    st.markdown(section_header("Key Indicators — 3yr Trend"), unsafe_allow_html=True)

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
            tc = trend_color(data["trend"], data["higher_is"])

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
    st.markdown(section_header("Indicator Cross-Correlations (36mo)"), unsafe_allow_html=True)

    with st.expander("Show Correlation Matrix", expanded=False):
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
