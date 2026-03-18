"""Portfolio Bridge — connect macro context to portfolio analysis."""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go


def render():
    st.markdown(
        '<h2>💼 <span style="background:linear-gradient(135deg,#818cf8,#a78bfa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent">'
        'Portfolio Bridge</span></h2>',
        unsafe_allow_html=True,
    )

    st.caption("Map portfolio holdings to country and sector exposures with macro context")

    # ── Portfolio input ───────────────────────────────────────────────────
    st.subheader("Portfolio Holdings")
    holdings_input = st.text_area(
        "Enter holdings (ticker,weight per line)",
        value="SPY,0.40\nBND,0.25\nVXUS,0.15\nVNQ,0.10\nGLD,0.10",
        height=150,
    )

    if st.button("🔗 Analyze Portfolio", type="primary"):
        # Parse holdings
        holdings = {}
        for line in holdings_input.strip().split("\n"):
            parts = line.strip().split(",")
            if len(parts) == 2:
                ticker = parts[0].strip().upper()
                try:
                    weight = float(parts[1].strip())
                    holdings[ticker] = weight
                except ValueError:
                    continue

        if not holdings:
            st.error("No valid holdings parsed. Use format: TICKER,weight")
            return

        total_weight = sum(holdings.values())
        st.write(f"**Portfolio:** {len(holdings)} holdings, total weight: {total_weight:.1%}")

        # ── Exposure mapping ──────────────────────────────────────────────
        with st.spinner("Resolving country & sector exposures..."):
            from macro_intel.bridge.exposure_mapper import map_portfolio
            country_map, sector_map = map_portfolio(holdings)

        col1, col2 = st.columns(2)

        # Country exposure
        with col1:
            st.subheader("Country Exposure")
            country_agg: dict[str, float] = {}
            for t, c in country_map.items():
                country_agg[c] = country_agg.get(c, 0) + holdings.get(t, 0)

            sorted_countries = sorted(country_agg.items(), key=lambda x: x[1], reverse=True)

            fig = go.Figure(go.Bar(
                x=[w for _, w in sorted_countries],
                y=[c for c, _ in sorted_countries],
                orientation="h",
                marker=dict(color="#818cf8"),
                text=[f"{w:.1%}" for _, w in sorted_countries],
                textposition="outside",
            ))
            fig.update_layout(
                height=max(250, len(sorted_countries) * 35),
                xaxis=dict(tickformat=".0%", title="Weight"),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e2e8f0"),
                margin=dict(l=20, r=60, t=10, b=30),
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig, use_container_width=True)

        # Sector exposure
        with col2:
            st.subheader("Sector Exposure")
            sector_agg: dict[str, float] = {}
            for t, s in sector_map.items():
                sector_agg[s] = sector_agg.get(s, 0) + holdings.get(t, 0)

            sorted_sectors = sorted(sector_agg.items(), key=lambda x: x[1], reverse=True)

            fig = go.Figure(go.Bar(
                x=[w for _, w in sorted_sectors],
                y=[s for s, _ in sorted_sectors],
                orientation="h",
                marker=dict(color="#a78bfa"),
                text=[f"{w:.1%}" for _, w in sorted_sectors],
                textposition="outside",
            ))
            fig.update_layout(
                height=max(250, len(sorted_sectors) * 35),
                xaxis=dict(tickformat=".0%", title="Weight"),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e2e8f0"),
                margin=dict(l=20, r=60, t=10, b=30),
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig, use_container_width=True)

        # ── Exposure network graph ────────────────────────────────────────
        st.divider()
        st.subheader("Exposure Network")
        with st.spinner("Building exposure network..."):
            try:
                from macro_intel.graphs.portfolio_exposure import build_portfolio_network
                from macro_intel.config.settings import settings

                path = build_portfolio_network(
                    holdings, country_map, sector_map,
                    output_path=settings.reports_dir / "portfolio_network.html",
                )
                html = open(path, encoding="utf-8").read()
                st.components.v1.html(html, height=650, scrolling=True)
            except Exception as e:
                st.warning(f"Could not generate network graph: {e}")

        # ── Holdings table ────────────────────────────────────────────────
        st.divider()
        st.subheader("Holdings Detail")
        import pandas as pd
        rows = []
        for ticker, weight in sorted(holdings.items(), key=lambda x: x[1], reverse=True):
            rows.append({
                "Ticker": ticker,
                "Weight": f"{weight:.1%}",
                "Country": country_map.get(ticker, "Unknown"),
                "Sector": sector_map.get(ticker, "Unknown"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
