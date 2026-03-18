"""Streamlit dashboard for Macro-Intel."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Macro-Intel",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    # ── Sidebar navigation ───────────────────────────────────────────────
    st.sidebar.markdown(
        '<h2 style="margin:0;padding:0">🧠 Macro-Intel</h2>'
        '<p style="color:#64748b;font-size:0.8em;margin-top:4px">'
        'Probabilistic Macro Intelligence</p>',
        unsafe_allow_html=True,
    )

    page = st.sidebar.radio(
        "Navigate",
        ["Regime Dashboard", "Feature Panel", "Network Graphs",
         "Drift Monitor", "Portfolio Bridge"],
        label_visibility="collapsed",
    )

    st.sidebar.divider()
    st.sidebar.caption("Built with PyMC · PyVis · Evidently · OpenBB")

    # ── Page routing ─────────────────────────────────────────────────────
    if page == "Regime Dashboard":
        from macro_intel.app.pages.regime_dashboard import render
        render()
    elif page == "Feature Panel":
        from macro_intel.app.pages.feature_panel_view import render
        render()
    elif page == "Network Graphs":
        from macro_intel.app.pages.network_view import render
        render()
    elif page == "Drift Monitor":
        from macro_intel.app.pages.drift_view import render
        render()
    elif page == "Portfolio Bridge":
        from macro_intel.app.pages.portfolio_bridge import render
        render()


if __name__ == "__main__":
    main()
