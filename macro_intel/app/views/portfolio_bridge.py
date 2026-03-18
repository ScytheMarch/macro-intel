"""Portfolio Bridge — map holdings to macro exposure with educational context."""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def render():
    from macro_intel.app.styles import (
        glass_card, section_header, badge, metric_card,
        TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, GREEN, RED, YELLOW, GRAY,
        ACCENT_INDIGO, ACCENT_VIOLET,
    )

    st.markdown(
        '<h2 style="margin:0 0 4px 0;font-weight:800;letter-spacing:-0.5px">'
        '💼 <span style="background:linear-gradient(135deg,#818cf8,#a78bfa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent">'
        'Portfolio Bridge</span></h2>'
        f'<div style="color:{TEXT_MUTED};font-size:0.78em;letter-spacing:0.3px;'
        f'margin-bottom:4px">See where your money is really exposed</div>',
        unsafe_allow_html=True,
    )

    # Educational intro
    with st.expander("ℹ️ What does the Portfolio Bridge do?", expanded=False):
        st.markdown("""
**It reveals the hidden geography and industry bets inside your portfolio.**

When you own an ETF like SPY (S&P 500), you're not just owning "US stocks" — you're
exposed to specific countries, sectors, and economic factors. This tool maps your
holdings to show you:

- **Country exposure**: Where in the world is your money actually invested?
- **Sector exposure**: Which industries would hurt you if they declined?
- **Concentration risk**: Are you more exposed to one area than you realize?

**For example:**
- Owning VXU (International) gives you exposure to Japan, UK, Germany, etc.
- Owning VNQ (Real Estate) makes you sensitive to interest rate changes
- Owning GLD (Gold) is often a hedge against inflation and crisis

**The network graph** shows this visually — you can see how your holdings connect
to countries and sectors, revealing hidden concentration.

**How to use it:**
1. Enter your portfolio holdings (ticker and weight)
2. Click "Analyze Portfolio"
3. Review your actual country and sector exposure
        """)

    # ── Input ─────────────────────────────────────────────────────────────
    col_input, col_info = st.columns([3, 2])

    with col_input:
        holdings_input = st.text_area(
            "Enter holdings (TICKER,weight per line)",
            value="SPY,0.40\nBND,0.25\nVXUS,0.15\nVNQ,0.10\nGLD,0.10",
            height=180,
            help="One holding per line. Format: TICKER,weight (e.g., SPY,0.40 means 40% in SPY)",
        )

    with col_info:
        st.markdown(
            glass_card(
                f'<div style="color:{TEXT_MUTED};font-size:0.72em;text-transform:uppercase;'
                f'letter-spacing:1.2px;font-weight:600;margin-bottom:8px">Quick Guide</div>'
                f'<div style="color:{TEXT_SECONDARY};font-size:0.82em;line-height:1.8">'
                f'<b>Format:</b> One holding per line<br>'
                f'<code style="color:{ACCENT_INDIGO}">TICKER,weight</code><br>'
                f'<b>Example:</b> <code style="color:{ACCENT_INDIGO}">SPY,0.40</code> = 40% in S&P 500<br>'
                f'<b>Weights</b> should add up to 1.0 (100%)<br>'
                f'Works with ETFs, stocks, and mutual funds</div>',
                border_color="rgba(99,102,241,0.15)",
            ),
            unsafe_allow_html=True,
        )

    # ── Common portfolio presets ───────────────────────────────────────────
    presets = {
        "Custom": "",
        "60/40 Classic": "SPY,0.60\nBND,0.40",
        "Three-Fund": "VTI,0.50\nVXUS,0.30\nBND,0.20",
        "All-Weather": "VTI,0.30\nTLT,0.40\nGLD,0.075\nDBC,0.075\nIEF,0.15",
        "Aggressive Growth": "QQQ,0.40\nSPY,0.30\nVXUS,0.20\nVNQ,0.10",
    }
    preset = st.selectbox(
        "Or try a preset portfolio",
        list(presets.keys()),
        help="Select a common portfolio allocation to see its exposure breakdown",
    )

    if st.button("🔗 Analyze Portfolio", type="primary"):
        # Use preset if selected
        text = presets.get(preset, "") if preset != "Custom" and presets.get(preset) else holdings_input

        # Parse
        holdings = {}
        for line in text.strip().split("\n"):
            parts = line.strip().split(",")
            if len(parts) == 2:
                ticker = parts[0].strip().upper()
                try:
                    weight = float(parts[1].strip())
                    holdings[ticker] = weight
                except ValueError:
                    continue

        if not holdings:
            st.error("No valid holdings parsed. Make sure each line has TICKER,weight format.")
            return

        total_weight = sum(holdings.values())

        # ── Summary metrics ───────────────────────────────────────────────
        s1, s2, s3 = st.columns(3)
        with s1:
            st.markdown(metric_card("Holdings", str(len(holdings)),
                                    sublabel="Number of positions"), unsafe_allow_html=True)
        with s2:
            color = GREEN if abs(total_weight - 1.0) < 0.02 else YELLOW
            status = "✅ Fully allocated" if abs(total_weight - 1.0) < 0.02 else "⚠️ Not 100%"
            st.markdown(metric_card("Total Weight", f"{total_weight:.1%}",
                                    color=color, sublabel=status),
                        unsafe_allow_html=True)
        with s3:
            top_ticker = max(holdings, key=holdings.get)
            st.markdown(metric_card("Largest Position",
                                    f"{holdings[top_ticker]:.1%}",
                                    sublabel=f"{top_ticker}"),
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

        # ── Interpretation ────────────────────────────────────────────────
        top_country = sorted_countries[0] if sorted_countries else ("Unknown", 0)
        top_sector = sorted_sectors[0] if sorted_sectors else ("Unknown", 0)

        # Concentration warnings
        warnings = []
        if top_country[1] > 0.7:
            warnings.append(f"⚠️ **{top_country[1]:.0%} concentrated in {top_country[0]}** — consider international diversification")
        if top_sector[1] > 0.5:
            warnings.append(f"⚠️ **{top_sector[1]:.0%} in {top_sector[0]}** sector — a downturn there would hit your portfolio hard")
        if len(country_agg) == 1:
            warnings.append("⚠️ **Single-country exposure** — you're fully dependent on one economy")

        if warnings:
            st.markdown(
                f'<div style="padding:12px 14px;background:rgba(234,179,8,0.08);border-radius:8px;'
                f'border-left:3px solid {YELLOW};margin-bottom:12px">'
                + "<br>".join(f'<div style="color:{TEXT_SECONDARY};font-size:0.88em">{w}</div>' for w in warnings)
                + '</div>',
                unsafe_allow_html=True,
            )

        if not warnings:
            st.markdown(
                f'<div style="padding:12px 14px;background:rgba(34,197,94,0.08);border-radius:8px;'
                f'border-left:3px solid {GREEN};margin-bottom:12px">'
                f'<div style="color:{TEXT_SECONDARY};font-size:0.88em">'
                f'✅ Portfolio looks reasonably diversified across '
                f'{len(country_agg)} countries and {len(sector_agg)} sectors.</div></div>',
                unsafe_allow_html=True,
            )

        # ── Donut + Bar Charts ────────────────────────────────────────────
        st.markdown(section_header("Exposure Breakdown"), unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                f'<div style="color:{TEXT_DIM};font-size:0.82em;margin-bottom:8px">'
                f'Which countries is your money invested in?</div>',
                unsafe_allow_html=True,
            )
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
            st.markdown(
                f'<div style="color:{TEXT_DIM};font-size:0.82em;margin-bottom:8px">'
                f'Which industries would hurt you if they declined?</div>',
                unsafe_allow_html=True,
            )
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
        st.markdown(
            f'<div style="color:{TEXT_DIM};font-size:0.82em;margin:-8px 0 12px 0">'
            f'This interactive graph shows how your holdings connect to countries and sectors. '
            f'<b>Dots</b> = your ETFs/stocks · <b>Diamonds</b> = countries · '
            f'<b>Triangles</b> = sectors · Line thickness = allocation size. Drag nodes to explore.</div>',
            unsafe_allow_html=True,
        )

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
        st.markdown(
            f'<div style="color:{TEXT_DIM};font-size:0.82em;margin:-8px 0 12px 0">'
            f'Each holding with its resolved country and sector classification.</div>',
            unsafe_allow_html=True,
        )

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
