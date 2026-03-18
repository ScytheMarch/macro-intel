"""Portfolio Bridge — connect regime outputs to portfolio context."""

from __future__ import annotations

import streamlit as st


def render():
    st.markdown(
        '<h2>💼 <span style="background:linear-gradient(135deg,#818cf8,#a78bfa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent">'
        'Portfolio Bridge</span></h2>',
        unsafe_allow_html=True,
    )

    st.caption("Connect macro regime outputs to portfolio analysis")

    from macro_intel.data import cache

    run = cache.get_latest_model_run()
    if not run:
        st.warning("No regime model found. Run `macro-intel fit` first.")
        return

    st.subheader("Current Regime Context")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Model", run["model_type"])
        st.metric("Countries", run["countries"])
    with col2:
        st.metric("Regimes", run["n_regimes"])
        st.metric("Last Run", run["timestamp"][:16])

    st.divider()

    # Portfolio input
    st.subheader("Portfolio Holdings")
    holdings_input = st.text_area(
        "Enter holdings (ticker,weight per line)",
        value="SPY,0.40\nBND,0.25\nVXUS,0.15\nVNQ,0.10\nGLD,0.10",
        height=150,
    )

    if st.button("🔗 Run Portfolio Bridge"):
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
            st.error("No valid holdings parsed.")
            return

        st.write(f"**Portfolio:** {len(holdings)} holdings, "
                 f"total weight: {sum(holdings.values()):.1%}")

        # Exposure mapping
        with st.spinner("Resolving exposures..."):
            from macro_intel.bridge.exposure_mapper import map_portfolio
            country_map, sector_map = map_portfolio(holdings)

        col1, col2 = st.columns(2)
        with col1:
            st.write("**Country Exposure:**")
            country_agg: dict[str, float] = {}
            for t, c in country_map.items():
                country_agg[c] = country_agg.get(c, 0) + holdings.get(t, 0)
            for c, w in sorted(country_agg.items(), key=lambda x: x[1], reverse=True):
                st.write(f"  {c}: {w:.1%}")

        with col2:
            st.write("**Sector Exposure:**")
            sector_agg: dict[str, float] = {}
            for t, s in sector_map.items():
                sector_agg[s] = sector_agg.get(s, 0) + holdings.get(t, 0)
            for s, w in sorted(sector_agg.items(), key=lambda x: x[1], reverse=True):
                st.write(f"  {s}: {w:.1%}")

        # Generate exposure graph
        with st.spinner("Building exposure network..."):
            from macro_intel.graphs.portfolio_exposure import build_portfolio_network
            from macro_intel.config.settings import settings

            path = build_portfolio_network(
                holdings, country_map, sector_map,
                output_path=settings.reports_dir / "portfolio_network.html",
            )
            html = open(path, encoding="utf-8").read()
            st.components.v1.html(html, height=600, scrolling=True)
