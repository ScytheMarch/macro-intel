"""Network Graph viewer — generate and view PyVis graphs on-the-fly."""

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
    from macro_intel.data import cache

    # Check if we have data
    test_date, test_val = cache.get_latest("UNRATE", "USA")
    has_data = test_val is not None

    if not has_data:
        st.info("No data available. Go to **Regime Dashboard** and click **Fetch Data** first.")
        return

    # ── Graph type selector ───────────────────────────────────────────────
    graph_type = st.selectbox(
        "Graph Type",
        ["Macro Dependency", "Indicator Correlations"],
    )

    col1, col2 = st.columns(2)
    with col1:
        min_corr = st.slider("Min Correlation", 0.1, 0.8, 0.3, 0.05)
    with col2:
        top_n = st.slider("Max Edges", 10, 100, 40, 5)

    if st.button("🕸️ Generate Graph", type="primary"):
        with st.spinner("Building network graph..."):
            if graph_type == "Macro Dependency":
                _generate_dependency_graph(settings, min_corr, top_n)
            else:
                _generate_correlation_heatmap()

    # ── Show existing graph if available ───────────────────────────────────
    reports_dir = settings.reports_dir
    graph_files = {
        "Macro Dependency": reports_dir / "macro_dependency.html",
    }

    for name, path in graph_files.items():
        if path.exists():
            st.subheader(name)
            html_content = path.read_text(encoding="utf-8")
            st.components.v1.html(html_content, height=750, scrolling=True)


def _generate_dependency_graph(settings, min_corr: float, top_n: int):
    """Generate macro dependency graph from cached data."""
    from macro_intel.analytics.correlations import build_indicator_correlation_matrix
    from macro_intel.graphs.macro_dependency import build_dependency_graph

    corr = build_indicator_correlation_matrix(country="USA", lookback_months=36)
    if corr.empty:
        st.warning("Not enough data to build correlation matrix.")
        return

    path = build_dependency_graph(
        corr,
        min_correlation=min_corr,
        top_n_edges=top_n,
        output_path=settings.reports_dir / "macro_dependency.html",
    )
    st.success(f"Graph generated with {len(corr.columns)} indicators")
    st.rerun()


def _generate_correlation_heatmap():
    """Show indicator correlation heatmap using Plotly."""
    import plotly.graph_objects as go
    from macro_intel.analytics.correlations import build_indicator_correlation_matrix
    from macro_intel.config.indicators import INDICATORS

    corr = build_indicator_correlation_matrix(country="USA", lookback_months=36)
    if corr.empty:
        st.warning("Not enough data for correlation analysis.")
        return

    # Rename for readability
    rename = {sid: INDICATORS[sid].name if sid in INDICATORS else sid for sid in corr.columns}
    corr = corr.rename(index=rename, columns=rename)

    fig = go.Figure(go.Heatmap(
        z=corr.values,
        x=corr.columns.tolist(),
        y=corr.index.tolist(),
        colorscale="RdBu_r",
        zmid=0, zmin=-1, zmax=1,
        text=corr.round(2).values,
        texttemplate="%{text}",
        textfont=dict(size=8),
    ))
    fig.update_layout(
        height=max(600, len(corr) * 25),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"),
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(tickangle=45, tickfont=dict(size=9)),
        yaxis=dict(tickfont=dict(size=9)),
    )
    st.plotly_chart(fig, use_container_width=True)
