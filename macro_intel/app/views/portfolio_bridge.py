"""Portfolio Bridge — map holdings to macro exposure with visual analytics."""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def render():
    from macro_intel.app.styles import (
        glass_card, section_header, badge, metric_card,
        TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, GREEN, RED, YELLOW, GRAY,
        ACCENT_INDIGO, ACCENT_VIOLET,
    )

    st.markdown(
        '<h2 style="margin:0 0 4px 0;font-weight:800;letter-spacing:-0.5px">'
        '💼 <span style="background:linear-gradient(135deg,#818cf8,#a78bfa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent">'
        'Portfolio Bridge</span></h2>'
        f'<div style="color:{TEXT_MUTED};font-size:0.78em;letter-spacing:0.3px;'
        f'margin-bottom:16px">Holdings → country & sector exposure mapping · '
        f'PyVis network visualization</div>',
        unsafe_allow_html=True,
    )

    # ── Input ─────────────────────────────────────────────────────────────
    col_input, col_info = st.columns([3, 2])

    with col_input:
        holdings_input = st.text_area(
            "Enter holdings (TICKER,weight per line)",
            value="SPY,0.40\nBND,0.25\nVXUS,0.15\nVNQ,0.10\nGLD,0.10",
            height=180,
        )

    with col_info:
        st.markdown(
            glass_card(
                f'<div style="color:{TEXT_MUTED};font-size:0.72em;text-transform:uppercase;'
                f'letter-spacing:1.2px;font-weight:600;margin-bottom:8px">Format Guide</div>'
                f'<div style="color:{TEXT_SECONDARY};font-size:0.82em;line-height:1.8">'
                f'One holding per line<br>'
                f'Format: <code style="color:{ACCENT_INDIGO}">TICKER,weight</code><br>'
                f'Example: <code style="color:{ACCENT_INDIGO}">SPY,0.40</code><br>'
                f'Weights should sum to 1.0<br>'
                f'ETFs, stocks, and funds supported</div>',
                border_color="rgba(99,102,241,0.15)",
            ),
            unsafe_allow_html=True,
        )

    if st.button("🔗 Analyze Portfolio", type="primary"):
        # Parse
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

        total_weight = sum(holdings.values())

        # ── Summary metrics ───────────────────────────────────────────────
        s1, s2, s3 = st.columns(3)
        with s1:
            st.markdown(metric_card("Holdings", str(len(holdings))), unsafe_allow_html=True)
        with s2:
            color = GREEN if abs(total_weight - 1.0) < 0.02 else YELLOW
            st.markdown(metric_card("Total Weight", f"{total_weight:.1%}", color=color),
                        unsafe_allow_html=True)
        with s3:
            st.markdown(metric_card("Largest Position",
                                    f"{max(holdings.values()):.1%}"),
                        unsafe_allow_html=True)

        st.markdown("", unsafe_allow_html=True)

        # ── Resolve exposures ─────────────────────────────────────────────
        with st.spinner("Resolving country & sector exposures..."):
            from macro_intel.bridge.exposure_mapper import map_portfolio
            country_map, sector_map = map_portfolio(holdings)

        # Aggregate
        country_agg: dict[str, float] = {}
        for t, c in country_map.items():
            country_agg[c] = country_agg.get(c, 0) + holdings.get(t, 0)
        sector_agg: dict[str, float] = {}
        for t, s in sector_map.items():
            sector_agg[s] = sector_agg.get(s, 0) + holdings.get(t, 0)

        sorted_countries = sorted(country_agg.items(), key=lambda x: x[1], reverse=True)
        sorted_sectors = sorted(sector_agg.items(), key=lambda x: x[1], reverse=True)

        # ── Donut + Bar Charts ────────────────────────────────────────────
        st.markdown(section_header("Exposure Breakdown"), unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            fig = make_subplots(rows=1, cols=2, specs=[[{"type": "pie"}, {"type": "bar"}]],
                                column_widths=[0.45, 0.55])

            fig.add_trace(go.Pie(
                labels=[c for c, _ in sorted_countries],
                values=[w for _, w in sorted_countries],
                hole=0.55,
                textinfo="label+percent",
                textfont=dict(size=10),
                marker=dict(colors=["#818cf8", "#a78bfa", "#c084fc", "#e879f9", "#f472b6",
                                     "#fb923c", "#fbbf24", "#34d399", "#22d3ee", "#60a5fa"]),
            ), row=1, col=1)

            fig.add_trace(go.Bar(
                x=[w for _, w in sorted_countries],
                y=[c for c, _ in sorted_countries],
                orientation="h",
                marker=dict(color="#818cf8"),
                text=[f"{w:.1%}" for _, w in sorted_countries],
                textposition="outside",
                showlegend=False,
            ), row=1, col=2)

            fig.update_layout(
                title=dict(text="Country Exposure", font=dict(size=14, color="#e2e8f0")),
                height=max(300, len(sorted_countries) * 35 + 80),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter", color="#94a3b8"),
                margin=dict(l=20, r=60, t=40, b=20),
                showlegend=False,
            )
            fig.update_yaxes(autorange="reversed", row=1, col=2)
            fig.update_xaxes(tickformat=".0%", row=1, col=2)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = make_subplots(rows=1, cols=2, specs=[[{"type": "pie"}, {"type": "bar"}]],
                                column_widths=[0.45, 0.55])

            fig.add_trace(go.Pie(
                labels=[s for s, _ in sorted_sectors],
                values=[w for _, w in sorted_sectors],
                hole=0.55,
                textinfo="label+percent",
                textfont=dict(size=10),
                marker=dict(colors=["#a78bfa", "#c084fc", "#e879f9", "#f472b6",
                                     "#fb923c", "#fbbf24", "#34d399", "#818cf8"]),
            ), row=1, col=1)

            fig.add_trace(go.Bar(
                x=[w for _, w in sorted_sectors],
                y=[s for s, _ in sorted_sectors],
                orientation="h",
                marker=dict(color="#a78bfa"),
                text=[f"{w:.1%}" for _, w in sorted_sectors],
                textposition="outside",
                showlegend=False,
            ), row=1, col=2)

            fig.update_layout(
                title=dict(text="Sector Exposure", font=dict(size=14, color="#e2e8f0")),
                height=max(300, len(sorted_sectors) * 35 + 80),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter", color="#94a3b8"),
                margin=dict(l=20, r=60, t=40, b=20),
                showlegend=False,
            )
            fig.update_yaxes(autorange="reversed", row=1, col=2)
            fig.update_xaxes(tickformat=".0%", row=1, col=2)
            st.plotly_chart(fig, use_container_width=True)

        # ── Exposure network ──────────────────────────────────────────────
        st.markdown(section_header("Exposure Network"), unsafe_allow_html=True)

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
                st.warning(f"Could not generate network: {e}")

        # ── Holdings detail table ─────────────────────────────────────────
        st.markdown(section_header("Holdings Detail"), unsafe_allow_html=True)

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
