"""Feature Panel browser — explore the unified macro data matrix with inline fetch."""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go


def render():
    st.markdown(
        '<h2>📊 <span style="background:linear-gradient(135deg,#818cf8,#a78bfa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent">'
        'Feature Panel</span></h2>',
        unsafe_allow_html=True,
    )

    from macro_intel.data.feature_panel import build_panel, get_panel_summary, PanelConfig
    from macro_intel.config.countries import COUNTRIES
    from macro_intel.config.indicators import get_fred_indicators
    from macro_intel.data import cache, fred_client

    # ── Check data availability ───────────────────────────────────────────
    test_date, test_val = cache.get_latest("UNRATE", "USA")
    has_data = test_val is not None

    if not has_data:
        st.info("No cached data. Fetch FRED data to populate the feature panel.")
        if st.button("📊 Fetch FRED Data", type="primary"):
            fred_ids = list(get_fred_indicators().keys())
            progress = st.progress(0, text="Fetching...")
            for i, sid in enumerate(fred_ids):
                try:
                    df = fred_client.fetch_series(sid, lookback_years=10)
                    if not df.empty:
                        cache.upsert_observations(sid, df, country="USA")
                except Exception:
                    pass
                progress.progress((i + 1) / len(fred_ids), text=f"Fetching {sid}...")
            progress.empty()
            st.success("Data fetched!")
            st.rerun()
        return

    # ── Controls ──────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        selected_countries = st.multiselect(
            "Countries",
            options=list(COUNTRIES.keys()),
            default=["USA"],
        )
    with col2:
        start_date = st.date_input("Start Date", value=None)

    if not selected_countries:
        st.info("Select at least one country.")
        return

    config = PanelConfig(
        countries=selected_countries,
        start_date=str(start_date) if start_date else "2000-01-01",
    )

    panel = build_panel(config)
    if panel.empty:
        st.warning("No data in panel for selected countries/dates.")
        return

    summary = get_panel_summary(panel)

    # ── Summary metrics ───────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rows", f"{summary['n_rows']:,}")
    m2.metric("Features", summary['n_features'])
    m3.metric("Countries", len(summary['countries']))
    m4.metric("Missing", f"{summary.get('missing_pct', 0):.1f}%")

    if summary.get("date_range"):
        st.caption(f"Date range: {summary['date_range'][0]} → {summary['date_range'][1]}")

    # ── Feature filter ────────────────────────────────────────────────────
    all_features = list(panel.columns)
    selected_features = st.multiselect(
        "Filter features",
        options=all_features,
        default=all_features[:10] if len(all_features) > 10 else all_features,
    )

    if selected_features:
        display_df = panel[selected_features].tail(60)
        st.dataframe(display_df, use_container_width=True, height=500)

        # ── Feature trend chart ───────────────────────────────────────────
        chart_feature = st.selectbox("Chart a feature", selected_features)
        if chart_feature:
            usa_data = panel.xs("USA", level="country") if "USA" in selected_countries else panel
            if chart_feature in usa_data.columns:
                series = usa_data[chart_feature].dropna()
                if not series.empty:
                    fig = go.Figure(go.Scatter(
                        x=series.index,
                        y=series.values,
                        mode="lines",
                        line=dict(color="#818cf8", width=2),
                        fill="tozeroy",
                        fillcolor="rgba(129,140,248,0.1)",
                    ))
                    fig.update_layout(
                        title=chart_feature,
                        height=350,
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#e2e8f0"),
                        margin=dict(l=40, r=20, t=40, b=30),
                    )
                    st.plotly_chart(fig, use_container_width=True)

    # ── Download ──────────────────────────────────────────────────────────
    csv = panel.to_csv()
    st.download_button(
        "📥 Download Panel CSV",
        data=csv,
        file_name="macro_intel_panel.csv",
        mime="text/csv",
    )
