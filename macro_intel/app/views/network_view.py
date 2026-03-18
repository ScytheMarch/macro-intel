"""Network Graph viewer — generate and explore PyVis macro graphs with educational context."""

from __future__ import annotations

import streamlit as st


def render():
    from macro_intel.app.styles import (
        glass_card, section_header, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    )
    from macro_intel.config.settings import settings
    from macro_intel.data import cache

    st.markdown(
        '<h2 style="margin:0 0 4px 0;font-weight:800;letter-spacing:-0.5px">'
        '🕸️ <span style="background:linear-gradient(135deg,#818cf8,#a78bfa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent">'
        'Network Graphs</span></h2>'
        f'<div style="color:{TEXT_MUTED};font-size:0.78em;letter-spacing:0.3px;'
        f'margin-bottom:4px">Interactive macro variable dependency networks</div>',
        unsafe_allow_html=True,
    )

    # Educational intro
    with st.expander("ℹ️ What are network graphs?", expanded=False):
        st.markdown("""
**Network graphs show how economic indicators are connected to each other.**

Imagine a web where each dot (node) is an economic measurement — unemployment, inflation, GDP, etc.
Lines (edges) between them show correlations — when one moves, the other tends to move too.

**How to read them:**
- **Green lines** = positive correlation (they move in the same direction)
- **Red lines** = negative correlation (when one goes up, the other goes down)
- **Thicker lines** = stronger relationship
- **Bigger dots** = more connections to other indicators
- **Clusters** = groups of indicators that move together

**Why is this useful?**
- See which parts of the economy are linked
- Find hidden relationships (e.g., housing starts predict manufacturing 6 months later)
- Identify "hub" indicators that influence everything else
- Understand how a shock in one area ripples through the economy

**You can drag nodes around** to explore the network interactively!
        """)

    test_date, test_val = cache.get_latest("UNRATE", "USA")
    if test_val is None:
        st.info("No data available. Go to **Regime Dashboard** and click **Fetch Data** first.")
        return

    # ── Controls ──────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        graph_type = st.selectbox("Graph Type", ["Macro Dependency", "Correlation Heatmap"])
    with col2:
        min_corr = st.slider(
            "Min Correlation",
            0.1, 0.8, 0.3, 0.05,
            help="Only show connections stronger than this value. Higher = fewer but stronger connections.",
        )
    with col3:
        top_n = st.slider(
            "Max Edges",
            10, 100, 40, 5,
            help="Maximum number of connections to display. More edges = more complex but more complete picture.",
        )

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
            f'<div style="color:{TEXT_SECONDARY};font-size:0.85em;margin:-8px 0 12px 0;'
            f'padding:10px 14px;background:rgba(255,255,255,0.02);border-radius:8px">'
            f'🟢 <b>Green lines</b> = indicators move together · '
            f'🔴 <b>Red lines</b> = indicators move opposite · '
            f'<b>Thicker lines</b> = stronger relationship · '
            f'<b>Drag nodes</b> to explore</div>',
            unsafe_allow_html=True,
        )
        html_content = dep_path.read_text(encoding="utf-8")
        st.components.v1.html(html_content, height=750, scrolling=True)

        # Interpretation help
        st.markdown(
            f'<div style="color:{TEXT_DIM};font-size:0.82em;margin-top:8px;'
            f'padding:10px;border-left:3px solid rgba(99,102,241,0.3);background:rgba(255,255,255,0.02);'
            f'border-radius:0 8px 8px 0">'
            f'<b>How to interpret:</b> Indicators with many thick connections are "hubs" — they influence '
            f'(or are influenced by) many other parts of the economy. The Fed Funds Rate, for example, '
            f'typically connects to everything because interest rates affect all borrowing and lending. '
            f'Isolated nodes with few connections tend to be more independent.</div>',
            unsafe_allow_html=True,
        )


def _generate_dependency(settings, min_corr, top_n):
    from macro_intel.analytics.correlations import build_indicator_correlation_matrix
    from macro_intel.graphs.macro_dependency import build_dependency_graph

    corr = build_indicator_correlation_matrix(country="USA", lookback_months=36)
    if corr.empty:
        st.warning("Not enough data for dependency graph.")
        return

    build_dependency_graph(corr, min_correlation=min_corr, top_n_edges=top_n,
                           output_path=settings.reports_dir / "macro_dependency.html")
    st.success(f"Graph generated — {len(corr.columns)} indicators, min correlation = {min_corr}")
    st.rerun()


def _generate_heatmap():
    import plotly.graph_objects as go
    from macro_intel.analytics.correlations import build_indicator_correlation_matrix
    from macro_intel.config.indicators import INDICATORS

    corr = build_indicator_correlation_matrix(country="USA", lookback_months=36)
    if corr.empty:
        st.warning("Not enough data.")
        return

    st.markdown(
        '<div style="color:#94a3b8;font-size:0.85em;margin-bottom:12px">'
        '<b>Reading the heatmap:</b> Each cell shows how strongly two indicators '
        'are correlated. <span style="color:#3b82f6">Blue = positive</span> (move together), '
        '<span style="color:#ef4444">Red = negative</span> (move opposite), '
        'White = no relationship.</div>',
        unsafe_allow_html=True,
    )

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
