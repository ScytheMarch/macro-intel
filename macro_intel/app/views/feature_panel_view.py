"""Feature Panel — data matrix browser with significance metrics and charts."""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
import numpy as np


def render():
    from macro_intel.app.styles import (
        glass_card, section_header, badge, metric_card, z_color,
        CATEGORY_COLORS, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, GREEN, YELLOW, RED, GRAY,
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
        f'margin-bottom:16px">Unified macro data matrix · '
        f'MultiIndex (date, country)</div>',
        unsafe_allow_html=True,
    )

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
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Rows", f"{summary['n_rows']:,}")
    m2.metric("Features", summary['n_features'])
    m3.metric("Countries", len(summary['countries']))
    m4.metric("Missing", f"{summary.get('missing_pct', 0):.1f}%")

    if summary.get("date_range"):
        m5.metric("Date Range", f"{summary['date_range'][0][:7]} → {summary['date_range'][1][:7]}")

    st.markdown("", unsafe_allow_html=True)

    # ── Category tabs ─────────────────────────────────────────────────────
    st.markdown(section_header("Feature Browser"), unsafe_allow_html=True)

    all_features = list(panel.columns)

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
    st.markdown(section_header("Feature Chart"), unsafe_allow_html=True)

    chart_feature = st.selectbox("Select feature to chart", all_features, key="chart_pick")
    if chart_feature and "USA" in selected_countries:
        usa_data = panel.xs("USA", level="country") if "USA" in panel.index.get_level_values("country") else panel
        if chart_feature in usa_data.columns:
            series = usa_data[chart_feature].dropna()
            if not series.empty:
                ind = INDICATORS.get(chart_feature)
                title = ind.name if ind else chart_feature

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
                        mode="lines", name="12mo MA",
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
