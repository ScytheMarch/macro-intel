"""Streamlit dashboard for Macro-Intel — Premium glass-on-dark theme."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Macro-Intel",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    from macro_intel.app.styles import GLOBAL_CSS

    # ── Inject premium CSS ────────────────────────────────────────────────
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    # ── Sidebar ───────────────────────────────────────────────────────────
    st.sidebar.markdown(
        '<div style="padding:8px 0">'
        '<h2 style="margin:0;padding:0;font-weight:800;letter-spacing:-0.5px">'
        '🧠 Macro-Intel</h2>'
        '<p style="color:#64748b;font-size:0.78em;margin:4px 0 0 0;'
        'letter-spacing:0.3px">Probabilistic Macro Intelligence</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    page = st.sidebar.radio(
        "Navigate",
        ["Regime Dashboard", "Feature Panel", "Network Graphs",
         "Drift Monitor", "Portfolio Bridge"],
        label_visibility="collapsed",
    )

    st.sidebar.divider()

    # Sidebar data controls
    from macro_intel.data import cache
    test_date, test_val = cache.get_latest("UNRATE", "USA")
    has_data = test_val is not None

    if has_data:
        st.sidebar.markdown(
            '<div style="color:#64748b;font-size:0.72em;text-transform:uppercase;'
            'letter-spacing:0.5px;margin-bottom:6px">Data Status</div>',
            unsafe_allow_html=True,
        )
        st.sidebar.markdown(
            f'<div style="color:#22c55e;font-size:0.8em">● Cache Active</div>'
            f'<div style="color:#64748b;font-size:0.72em">Last: {test_date}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            '<div style="color:#ef4444;font-size:0.8em">● No Data Cached</div>',
            unsafe_allow_html=True,
        )

    st.sidebar.divider()
    st.sidebar.caption(
        '<div style="color:#475569;font-size:0.7em;letter-spacing:0.3px">'
        'Built with PyMC · PyVis · Evidently · OpenBB</div>',
        unsafe_allow_html=True,
    )

    # ── Page routing ──────────────────────────────────────────────────────
    if page == "Regime Dashboard":
        from macro_intel.app.views.regime_dashboard import render
        render()
    elif page == "Feature Panel":
        from macro_intel.app.views.feature_panel_view import render
        render()
    elif page == "Network Graphs":
        from macro_intel.app.views.network_view import render
        render()
    elif page == "Drift Monitor":
        from macro_intel.app.views.drift_view import render
        render()
    elif page == "Portfolio Bridge":
        from macro_intel.app.views.portfolio_bridge import render
        render()


if __name__ == "__main__":
    main()
