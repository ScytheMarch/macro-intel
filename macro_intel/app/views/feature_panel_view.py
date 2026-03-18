"""Feature Panel — data matrix browser with significance metrics, charts, and educational context."""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
import numpy as np


def render():
    from macro_intel.app.styles import (
        glass_card, section_header, badge, metric_card, z_color,
        CATEGORY_COLORS, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, GREEN, YELLOW, RED, GRAY,
    )
    from macro_intel.data.feature_panel import build_panel, get_panel_summary, PanelConfig
    from macro_intel.config.countries import COUNTRIES
    from macro_intel.config.indicators import get_fred_indicators, INDICATORS
    from macro_intel.data import cache, fred_client

    st.markdown(
        '<h2 style="margin:0 0 4px 0;font-weight:800;letter-spacing:-0.5px">'
        '📊 <span style="background:linear-gradient(135deg,#818cf8,#a78bfa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent">'
        'Feature Panel</span></h2>'
        f'<div style="color:{TEXT_MUTED};font-size:0.78em;letter-spacing:0.3px;'
        f'margin-bottom:4px">Unified macro data matrix · '
        f'All indicators in one place</div>',
        unsafe_allow_html=True,
    )

    # Educational intro
    with st.expander("ℹ️ What is the Feature Panel?", expanded=False):
        st.markdown("""
**Think of it as a spreadsheet of the entire economy.**

This page organizes all 30+ economic indicators into a structured data table — like a giant Excel sheet
where each row is a month and each column is a different economic measurement (unemployment, inflation,
GDP, interest rates, etc.).

**Why is this useful?**
- **Spot patterns**: See how different parts of the economy move together or apart over time
- **Track history**: View years of economic data at a glance
- **Research**: Download the raw data for your own analysis
- **Categories**: Browse by topic — Inflation, Labor, Output, Consumer, etc.

**Reading the cards:**
- Each indicator card shows the **latest value** and its **Z-score** (how unusual the reading is)
- The colored bar under each card: 🟢 green = normal, 🟡 yellow = noteworthy, 🔴 red = extreme
        """)

    # ── Check data ────────────────────────────────────────────────────────
    test_date, test_val = cache.get_latest("UNRATE", "USA")
    if test_val is None:
        st.info("No data cached. Go to **Regime Dashboard** and click **Fetch Data** first.")
        return

    # ── Controls ──────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        selected_countries = st.multiselect("Countries", list(COUNTRIES.keys()), default=["USA"])
    with col2:
        start_date = st.date_input("Start Date", value=None)
    with col3:
        time_range = st.selectbox("Quick Range", ["All", "1Y", "2Y", "3Y", "5Y", "10Y"], index=3)

    if not selected_countries:
        st.info("Select at least one country.")
        return

    # Resolve start date from quick range
    if time_range != "All" and start_date is None:
        import datetime
        years = int(time_range.replace("Y", ""))
        start_str = (datetime.date.today() - datetime.timedelta(days=years * 365)).isoformat()
    elif start_date:
        start_str = str(start_date)
    else:
        start_str = "2000-01-01"

    config = PanelConfig(countries=selected_countries, start_date=start_str)
    panel = build_panel(config)

    if panel.empty:
        st.warning("No data in panel for selected parameters.")
        return

    summary = get_panel_summary(panel)

    # ── Summary metrics ───────────────────────────────────────────────────
    st.markdown(
        f'<div style="color:{TEXT_DIM};font-size:0.82em;margin-bottom:10px">'
        f'The panel below contains <b style="color:{TEXT_PRIMARY}">{summary["n_rows"]:,}</b> data points '
        f'across <b style="color:{TEXT_PRIMARY}">{summary["n_features"]}</b> indicators '
        f'for <b style="color:{TEXT_PRIMARY}">{len(summary["countries"])}</b> country/countries.</div>',
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Data Points", f"{summary['n_rows']:,}")
    m2.metric("Indicators", summary['n_features'])
    m3.metric("Countries", len(summary['countries']))
    m4.metric("Missing Data", f"{summary.get('missing_pct', 0):.1f}%")

    if summary.get("date_range"):
        m5.metric("Date Range", f"{summary['date_range'][0][:7]} → {summary['date_range'][1][:7]}")

    st.markdown("", unsafe_allow_html=True)

    # ── Category tabs ─────────────────────────────────────────────────────
    st.markdown(section_header("Browse by Category"), unsafe_allow_html=True)

    all_features = list(panel.columns)

    # Category descriptions for context
    cat_descriptions = {
        "Inflation": "**Prices & Cost of Living** — Is the purchasing power of your dollar shrinking? These indicators track price changes across the economy.",
        "Labor": "**Jobs & Employment** — The heartbeat of the economy. Strong employment = consumers spend = businesses grow.",
        "Output": "**Economic Production** — How much stuff is the economy actually making? GDP, factory output, and capacity.",
        "Consumer": "**Spending & Confidence** — What are Americans buying and how do they feel? Consumer spending = 70% of GDP.",
        "Monetary": "**Federal Reserve & Money** — The Fed's toolkit: interest rates and money supply. These drive everything else.",
        "Fixed Income": "**Bonds & Yields** — Bond markets are smarter than stock markets. The yield curve has predicted every recession since 1970.",
        "Market": "**Stocks & Volatility** — Fear, greed, and the VIX. Market indicators reflect real-time investor sentiment.",
        "Housing": "**Real Estate** — Housing is a leading indicator. It turns down 6-12 months before recessions start.",
        "Trade": "**International Trade** — How the US trades with the world. Trade deficits, exchange rates, and global flows.",
        "Regime": "**Economic Cycle** — Official recession indicators from the National Bureau of Economic Research (NBER).",
    }

    # Group features by category
    by_cat: dict[str, list[str]] = {}
    for feat in all_features:
        ind = INDICATORS.get(feat)
        cat = ind.category if ind else "Other"
        by_cat.setdefault(cat, []).append(feat)

    cat_names = sorted(by_cat.keys())
    tabs = st.tabs(["All"] + cat_names)

    # All tab
    with tabs[0]:
        st.markdown(
            f'<div style="color:{TEXT_SECONDARY};font-size:0.85em;margin-bottom:12px">'
            f'Showing all {len(all_features)} indicators. Use the filter below to narrow down, '
            f'or click a category tab above to focus on a specific area of the economy.</div>',
            unsafe_allow_html=True,
        )
        selected_features = st.multiselect(
            "Filter features", all_features,
            default=all_features[:12] if len(all_features) > 12 else all_features,
            key="feat_all",
        )
        if selected_features:
            _show_feature_table(panel, selected_features, INDICATORS, z_color, TEXT_MUTED)

    # Category tabs
    for tab, cat in zip(tabs[1:], cat_names):
        with tab:
            # Category explanation
            desc = cat_descriptions.get(cat, "")
            if desc:
                st.markdown(
                    f'<div style="color:{TEXT_SECONDARY};font-size:0.88em;margin-bottom:14px;'
                    f'padding:10px 14px;background:rgba(255,255,255,0.02);border-radius:8px;'
                    f'border-left:3px solid {CATEGORY_COLORS.get(cat, GRAY)}">'
                    f'{desc}</div>',
                    unsafe_allow_html=True,
                )

            cat_features = by_cat[cat]
            cat_color = CATEGORY_COLORS.get(cat, GRAY)

            # Feature stats cards
            if "USA" in selected_countries:
                usa_data = panel.xs("USA", level="country") if "USA" in panel.index.get_level_values("country") else panel
                cols = st.columns(min(4, len(cat_features)))
                for i, feat in enumerate(cat_features[:8]):
                    with cols[i % min(4, len(cat_features))]:
                        if feat in usa_data.columns:
                            series = usa_data[feat].dropna()
                            if not series.empty:
                                val = series.iloc[-1]
                                z = _quick_z(series)
                                zc = z_color(z) if z is not None else GRAY
                                ind = INDICATORS.get(feat)
                                label = ind.name if ind else feat

                                st.metric(label, f"{val:.2f}",
                                          delta=f"{z:+.1f}σ" if z else None)
                                st.markdown(
                                    f'<div style="height:3px;background:{zc};'
                                    f'border-radius:2px;margin:-8px 0 8px 0;opacity:0.7"></div>',
                                    unsafe_allow_html=True,
                                )

            _show_feature_table(panel, cat_features, INDICATORS, z_color, TEXT_MUTED)

    # ── Feature chart ─────────────────────────────────────────────────────
    st.markdown(section_header("Chart Any Indicator"), unsafe_allow_html=True)
    st.markdown(
        f'<div style="color:{TEXT_DIM};font-size:0.82em;margin:-8px 0 12px 0">'
        f'Select any indicator below to see its full history. The dashed yellow line is the 12-month '
        f'moving average — it smooths out noise to show the underlying trend.</div>',
        unsafe_allow_html=True,
    )

    chart_feature = st.selectbox("Select feature to chart", all_features, key="chart_pick")
    if chart_feature and "USA" in selected_countries:
        usa_data = panel.xs("USA", level="country") if "USA" in panel.index.get_level_values("country") else panel
        if chart_feature in usa_data.columns:
            series = usa_data[chart_feature].dropna()
            if not series.empty:
                ind = INDICATORS.get(chart_feature)
                title = ind.name if ind else chart_feature
                desc = ind.description if ind else ""

                if desc:
                    st.markdown(
                        f'<div style="color:{TEXT_SECONDARY};font-size:0.85em;margin-bottom:8px">'
                        f'📖 {desc}</div>',
                        unsafe_allow_html=True,
                    )

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=series.index, y=series.values,
                    mode="lines", name=title,
                    line=dict(color="#818cf8", width=2),
                    fill="tozeroy", fillcolor="rgba(129,140,248,0.08)",
                ))

                # Add moving averages
                if len(series) > 12:
                    ma12 = series.rolling(12).mean()
                    fig.add_trace(go.Scatter(
                        x=ma12.index, y=ma12.values,
                        mode="lines", name="12mo Moving Average",
                        line=dict(color="#f59e0b", width=1.5, dash="dash"),
                    ))

                fig.update_layout(
                    title=dict(text=title, font=dict(size=14, color="#e2e8f0")),
                    height=380,
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter", color="#94a3b8"),
                    margin=dict(l=60, r=20, t=50, b=40),
                    xaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
                    hovermode="x unified",
                    hoverlabel=dict(bgcolor="#1e1b4b", font_size=11, bordercolor="#818cf8"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(fig, use_container_width=True)

    # ── Download ──────────────────────────────────────────────────────────
    st.divider()
    st.markdown(
        f'<div style="color:{TEXT_DIM};font-size:0.82em;margin-bottom:8px">'
        f'📥 Download the full dataset as a CSV file for use in Excel, Python, R, or any spreadsheet tool.</div>',
        unsafe_allow_html=True,
    )
    csv = panel.to_csv()
    st.download_button("📥 Download Panel CSV", data=csv,
                       file_name="macro_intel_panel.csv", mime="text/csv")


def _quick_z(series, window=60):
    if len(series) < 12:
        return None
    w = min(window, len(series))
    recent = series.tail(w)
    mean, std = recent.mean(), recent.std()
    if std == 0 or np.isnan(std):
        return None
    return float((series.iloc[-1] - mean) / std)


def _show_feature_table(panel, features, INDICATORS, z_color, TEXT_MUTED):
    """Show filtered dataframe with feature data."""
    valid = [f for f in features if f in panel.columns]
    if valid:
        st.dataframe(
            panel[valid].tail(60),
            use_container_width=True,
            height=400,
        )
