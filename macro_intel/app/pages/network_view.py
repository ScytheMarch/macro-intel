"""Network Graph viewer — embed PyVis HTML outputs."""

from __future__ import annotations

import streamlit as st
from pathlib import Path


def render():
    st.markdown(
        '<h2>🕸️ <span style="background:linear-gradient(135deg,#818cf8,#a78bfa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent">'
        'Network Graphs</span></h2>',
        unsafe_allow_html=True,
    )

    from macro_intel.config.settings import settings

    reports_dir = settings.reports_dir

    # List available graphs
    graph_files = {
        "Macro Dependency": reports_dir / "macro_dependency.html",
        "Country Contagion": reports_dir / "contagion_network.html",
        "Portfolio Exposure": reports_dir / "portfolio_network.html",
    }

    available = {name: path for name, path in graph_files.items() if path.exists()}

    if not available:
        st.warning("No network graphs generated yet. Run `macro-intel graphs` from the CLI.")
        st.code("macro-intel graphs", language="bash")
        return

    selected = st.selectbox("Select Graph", list(available.keys()))

    if selected and selected in available:
        html_path = available[selected]
        html_content = html_path.read_text(encoding="utf-8")
        st.components.v1.html(html_content, height=750, scrolling=True)

        st.caption(f"Source: {html_path}")
