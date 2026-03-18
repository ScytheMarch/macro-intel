"""Network Graph viewer — generate and explore PyVis macro graphs."""

from __future__ import annotations

import streamlit as st


def render():
    from macro_intel.app.styles import (
        glass_card, section_header, TEXT_MUTED, TEXT_PRIMARY,
    )
    from macro_intel.config.settings import settings
    from macro_intel.data import cache

    st.markdown(
        '<h2 style="margin:0 0 4px 0;font-weight:800;letter-spacing:-0.5px">'
        '🕸️ <span style="background:linear-gradient(135deg,#818cf8,#a78bfa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent">'
        'Network Graphs</span></h2>'
        f'<div style="color:{TEXT_MUTED};font-size:0.78em;letter-spacing:0.3px;'
        f'margin-bottom:16px">Interactive macro variable dependency networks · '
        f'Powered by PyVis</div>',
        unsafe_allow_html=True,
    )

    test_date, test_val = cache.get_latest("UNRATE", "USA")
    if test_val is None:
        st.info("No data available. Go to **Regime Dashboard** and click **Fetch Data** first.")
        return

    # ── Controls ──────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        graph_type = st.selectbox("Graph Type", ["Macro Dependency", "Correlation Heatmap"])
    with col2:
        min_corr = st.slider("Min Correlation", 0.1, 0.8, 0.3, 0.05)
    with col3:
        top_n = st.slider("Max Edges", 10, 100, 40, 5)

    if st.button("🕸️ Generate Graph", type="primary"):
        with st.spinner("Building network..."):
            if graph_type == "Macro Dependency":
                _generate_dependency(settings, min_corr, top_n)
            else:
                _generate_heatmap()

    # ── Show existing graph ───────────────────────────────────────────────
    dep_path = settings.reports_dir / "macro_dependency.html"
    if dep_path.exists():
        st.markdown(section_header("Macro Variable Dependencies"), unsafe_allow_html=True)
        st.markdown(
            f'<div style="color:{TEXT_MUTED};font-size:0.78em;margin-bottom:8px">'
            f'Nodes = indicators · Edges = correlations · '
            f'Green = positive · Red = negative · Width = strength</div>',
            unsafe_allow_html=True,
        )
        html_content = dep_path.read_text(encoding="utf-8")
        st.components.v1.html(html_content, height=750, scrolling=True)


def _generate_dependency(settings, min_corr, top_n):
    from macro_intel.analytics.correlations import build_indicator_correlation_matrix
    from macro_intel.graphs.macro_dependency import build_dependency_graph

    corr = build_indicator_correlation_matrix(country="USA", lookback_months=36)
    if corr.empty:
        st.warning("Not enough data for dependency graph.")
        return

    build_dependency_graph(corr, min_correlation=min_corr, top_n_edges=top_n,
                           output_path=settings.reports_dir / "macro_dependency.html")
    st.success(f"Graph generated — {len(corr.columns)} indicators, min r={min_corr}")
    st.rerun()


def _generate_heatmap():
    import plotly.graph_objects as go
    from macro_intel.analytics.correlations import build_indicator_correlation_matrix
    from macro_intel.config.indicators import INDICATORS

    corr = build_indicator_correlation_matrix(country="USA", lookback_months=36)
    if corr.empty:
        st.warning("Not enough data.")
        return

    rename = {sid: INDICATORS[sid].name if sid in INDICATORS else sid for sid in corr.columns}
    corr = corr.rename(index=rename, columns=rename)

    fig = go.Figure(go.Heatmap(
        z=corr.values, x=corr.columns.tolist(), y=corr.index.tolist(),
        colorscale="RdBu_r", zmid=0, zmin=-1, zmax=1,
        text=corr.round(2).values, texttemplate="%{text}",
        textfont=dict(size=8),
    ))
    fig.update_layout(
        height=max(600, len(corr) * 22),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#94a3b8"),
        margin=dict(l=20, r=20, t=10, b=10),
        xaxis=dict(tickangle=45, tickfont=dict(size=9)),
        yaxis=dict(tickfont=dict(size=9)),
    )
    st.plotly_chart(fig, use_container_width=True)
