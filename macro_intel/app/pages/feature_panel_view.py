"""Feature Panel browser — explore the unified macro data matrix."""

from __future__ import annotations

import streamlit as st


def render():
    st.markdown(
        '<h2>📊 <span style="background:linear-gradient(135deg,#818cf8,#a78bfa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent">'
        'Feature Panel</span></h2>',
        unsafe_allow_html=True,
    )

    from macro_intel.data.feature_panel import build_panel, get_panel_summary, PanelConfig
    from macro_intel.config.countries import COUNTRIES

    # Controls
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
        st.warning("No data in panel. Run `macro-intel fetch` first.")
        return

    summary = get_panel_summary(panel)

    # Summary metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rows", f"{summary['n_rows']:,}")
    m2.metric("Features", summary['n_features'])
    m3.metric("Countries", len(summary['countries']))
    m4.metric("Missing", f"{summary.get('missing_pct', 0):.1f}%")

    if summary.get("date_range"):
        st.caption(f"Date range: {summary['date_range'][0]} → {summary['date_range'][1]}")

    # Feature filter
    all_features = list(panel.columns)
    selected_features = st.multiselect(
        "Filter features",
        options=all_features,
        default=all_features[:10] if len(all_features) > 10 else all_features,
    )

    if selected_features:
        st.dataframe(
            panel[selected_features].tail(60),
            use_container_width=True,
            height=500,
        )

    # Download
    csv = panel.to_csv()
    st.download_button(
        "📥 Download Panel CSV",
        data=csv,
        file_name="macro_intel_panel.csv",
        mime="text/csv",
    )
