"""Currency Monitor — real-time forex pairs with charts and analysis."""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# Major forex pairs with human-readable labels
FOREX_PAIRS = {
    "DX-Y.NYB":   {"label": "US Dollar Index (DXY)",     "base": "USD", "quote": "Basket", "explain": "Measures the dollar against a basket of 6 major currencies. Rising = dollar strengthening globally."},
    "EURUSD=X":   {"label": "Euro / US Dollar",          "base": "EUR", "quote": "USD",    "explain": "How many dollars one euro buys. Rising = euro strengthening, dollar weakening."},
    "USDJPY=X":   {"label": "US Dollar / Japanese Yen",  "base": "USD", "quote": "JPY",    "explain": "How many yen one dollar buys. Rising = dollar strengthening vs yen."},
    "GBPUSD=X":   {"label": "British Pound / US Dollar", "base": "GBP", "quote": "USD",    "explain": "How many dollars one pound buys. Rising = pound strengthening."},
    "USDCHF=X":   {"label": "US Dollar / Swiss Franc",   "base": "USD", "quote": "CHF",    "explain": "How many francs one dollar buys. The franc is a safe-haven currency."},
    "AUDUSD=X":   {"label": "Australian Dollar / USD",   "base": "AUD", "quote": "USD",    "explain": "Commodity-linked currency. Rises when global growth and commodity demand are strong."},
    "USDCAD=X":   {"label": "US Dollar / Canadian Dollar","base": "USD", "quote": "CAD",   "explain": "Canada is a major oil exporter — CAD strengthens when oil prices rise."},
    "NZDUSD=X":   {"label": "New Zealand Dollar / USD",  "base": "NZD", "quote": "USD",    "explain": "Commodity and dairy-linked. Sensitive to Chinese demand and global risk appetite."},
    "USDCNY=X":   {"label": "US Dollar / Chinese Yuan",  "base": "USD", "quote": "CNY",    "explain": "Managed by China's central bank. Rising = yuan weakening, often signals trade tensions."},
    "USDINR=X":   {"label": "US Dollar / Indian Rupee",  "base": "USD", "quote": "INR",    "explain": "India's currency. Weakens during oil price spikes (India imports most of its oil)."},
    "USDMXN=X":   {"label": "US Dollar / Mexican Peso",  "base": "USD", "quote": "MXN",    "explain": "Popular carry trade currency. Sensitive to US-Mexico trade policy and remittances."},
    "USDBRL=X":   {"label": "US Dollar / Brazilian Real", "base": "USD", "quote": "BRL",    "explain": "Commodity-linked emerging market currency. Volatile during political uncertainty."},
}

# Preset groups
PAIR_GROUPS = {
    "Major Pairs": ["DX-Y.NYB", "EURUSD=X", "USDJPY=X", "GBPUSD=X"],
    "Safe Havens": ["USDJPY=X", "USDCHF=X", "DX-Y.NYB"],
    "Commodity Currencies": ["AUDUSD=X", "USDCAD=X", "NZDUSD=X"],
    "Emerging Markets": ["USDCNY=X", "USDINR=X", "USDMXN=X", "USDBRL=X"],
    "All Pairs": list(FOREX_PAIRS.keys()),
}


def render():
    from macro_intel.app.styles import (
        glass_card, section_header, badge, metric_card,
        TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, GREEN, RED, YELLOW, GRAY,
        ACCENT_INDIGO,
    )

    st.markdown(
        '<h2 style="margin:0 0 4px 0;font-weight:800;letter-spacing:-0.5px">'
        '💱 <span style="background:linear-gradient(135deg,#818cf8,#a78bfa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent">'
        'Currency Monitor</span></h2>'
        f'<div style="color:{TEXT_MUTED};font-size:0.78em;letter-spacing:0.3px;'
        f'margin-bottom:4px">Live forex rates · Dollar strength · Currency trends</div>',
        unsafe_allow_html=True,
    )

    # Educational intro
    with st.expander("ℹ️ How to read currency markets", expanded=False):
        st.markdown("""
**Currencies trade in pairs** — you're always comparing one currency to another.

**EUR/USD = 1.08** means 1 Euro buys 1.08 US Dollars. If it rises to 1.10, the Euro got
stronger (or the Dollar got weaker).

**Why do currencies matter for macro?**
- **Strong Dollar** = US imports cheaper, exports harder to sell, emerging markets struggle (their dollar-denominated debt gets more expensive)
- **Weak Dollar** = US exports more competitive, commodity prices tend to rise, emerging markets breathe easier
- **Yen strengthening** = often a sign of global risk-off (investors fleeing to safety)
- **Commodity currencies** (AUD, CAD, NZD) = rise when global growth is strong and demand for raw materials increases

**The DXY (Dollar Index)** is the single most important number — it tracks the dollar against
a basket of 6 major currencies (Euro, Yen, Pound, Canadian Dollar, Swiss Franc, Swedish Krona).

**Key signals:**
- 🟢 DXY falling + stocks rising = risk-on environment, good for growth
- 🔴 DXY spiking + stocks falling = flight to safety, stress in global markets
- ⚠️ Yen strengthening rapidly = investors are scared, unwinding carry trades
        """)

    # ── Controls ─────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        group = st.selectbox(
            "Currency Group",
            list(PAIR_GROUPS.keys()),
            index=0,
            help="Select a group of currency pairs to monitor",
        )

    with col2:
        period = st.selectbox(
            "Time Period",
            ["1D", "5D", "1M", "3M", "6M", "1Y", "2Y", "5Y"],
            index=3,
            key="fx_period",
            help="How far back to look",
        )

    with col3:
        interval_map = {
            "1D": "5m", "5D": "15m", "1M": "1d", "3M": "1d",
            "6M": "1d", "1Y": "1wk", "2Y": "1wk", "5Y": "1mo",
        }
        interval = interval_map.get(period, "1d")
        st.markdown(
            f'<div style="color:{TEXT_DIM};font-size:0.78em;padding-top:28px">'
            f'Interval: <b>{interval}</b></div>',
            unsafe_allow_html=True,
        )

    selected_tickers = PAIR_GROUPS.get(group, PAIR_GROUPS["Major Pairs"])

    if st.button("💱 Load Currency Data", type="primary"):
        _fetch_and_display(selected_tickers, period, interval, FOREX_PAIRS,
                           glass_card, section_header, badge, metric_card,
                           TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
                           GREEN, RED, YELLOW, GRAY, ACCENT_INDIGO)
    else:
        # Show prompt
        st.markdown(
            glass_card(
                f'<div style="text-align:center;padding:20px">'
                f'<div style="font-size:1.5em;margin-bottom:8px">💱</div>'
                f'<div style="color:{TEXT_PRIMARY};font-size:0.95em;font-weight:500">'
                f'Click <b>Load Currency Data</b> to see live forex rates</div>'
                f'<div style="color:{TEXT_MUTED};font-size:0.82em;margin-top:6px">'
                f'Data pulled from Yahoo Finance in real-time</div>'
                f'</div>',
                border_color="rgba(99,102,241,0.15)",
            ),
            unsafe_allow_html=True,
        )


def _fetch_and_display(tickers, period, interval, FOREX_PAIRS,
                       glass_card, section_header, badge, metric_card,
                       TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
                       GREEN, RED, YELLOW, GRAY, ACCENT_INDIGO):
    """Fetch forex data and render all visualizations."""
    import yfinance as yf
    import pandas as pd
    import numpy as np

    with st.spinner("Fetching live currency data..."):
        try:
            raw = yf.download(tickers, period=period, interval=interval, progress=False)
        except Exception as e:
            st.error(f"Failed to fetch currency data: {e}")
            return

    if raw.empty:
        st.warning("No currency data returned. Try a different period.")
        return

    # Extract close prices — handle single vs multi ticker
    if isinstance(raw.columns, pd.MultiIndex):
        closes = raw["Close"] if "Close" in raw.columns.get_level_values(0) else raw
        # Flatten if needed
        if isinstance(closes.columns, pd.MultiIndex):
            closes.columns = closes.columns.get_level_values(-1)
    else:
        closes = raw[["Close"]].rename(columns={"Close": tickers[0]}) if len(tickers) == 1 else raw

    # Ensure we have a clean DataFrame
    if isinstance(closes, pd.Series):
        closes = closes.to_frame(name=tickers[0])

    # ── Summary Cards ────────────────────────────────────────────────
    st.markdown(section_header("Current Rates & Changes"), unsafe_allow_html=True)
    st.markdown(
        f'<div style="color:{TEXT_DIM};font-size:0.82em;margin:-8px 0 12px 0">'
        f'Live rates from Yahoo Finance. Green = currency pair rose (base strengthened). '
        f'Red = pair fell (base weakened).</div>',
        unsafe_allow_html=True,
    )

    n_cols = min(4, len(tickers))
    cols = st.columns(n_cols)

    pair_data = {}  # Store computed data for charts

    for i, ticker in enumerate(tickers):
        if ticker not in closes.columns:
            continue

        series = closes[ticker].dropna()
        if len(series) < 2:
            continue

        latest = float(series.iloc[-1])
        prev = float(series.iloc[0])
        change = latest - prev
        pct_change = (change / prev) * 100 if prev != 0 else 0
        color = GREEN if change >= 0 else RED
        arrow = "▲" if change >= 0 else "▼"
        meta = FOREX_PAIRS.get(ticker, {})
        label = meta.get("label", ticker)

        pair_data[ticker] = {
            "series": series,
            "latest": latest,
            "change": change,
            "pct_change": pct_change,
            "label": label,
        }

        with cols[i % n_cols]:
            st.markdown(
                f'<div style="background:linear-gradient(135deg,rgba(255,255,255,0.04),rgba(255,255,255,0.015));'
                f'border:1px solid rgba(255,255,255,0.08);border-left:4px solid {color};'
                f'border-radius:0 12px 12px 0;padding:14px 16px;margin-bottom:8px">'
                f'<div style="color:{TEXT_MUTED};font-size:0.72em;text-transform:uppercase;'
                f'letter-spacing:0.5px;margin-bottom:4px">{label}</div>'
                f'<div style="color:{TEXT_PRIMARY};font-size:1.6em;font-weight:700">'
                f'{latest:.4f}</div>'
                f'<div style="color:{color};font-size:0.88em;font-weight:600;margin-top:2px">'
                f'{arrow} {abs(change):.4f} ({pct_change:+.2f}%)</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    if not pair_data:
        st.warning("No data available for selected pairs.")
        return

    # ── Price Charts ─────────────────────────────────────────────────
    st.markdown(section_header("Price Charts"), unsafe_allow_html=True)
    st.markdown(
        f'<div style="color:{TEXT_DIM};font-size:0.82em;margin:-8px 0 12px 0">'
        f'Each chart shows the exchange rate over the selected period. '
        f'The dashed line is the moving average.</div>',
        unsafe_allow_html=True,
    )

    chart_cols = st.columns(2)
    for i, (ticker, pdata) in enumerate(pair_data.items()):
        with chart_cols[i % 2]:
            series = pdata["series"]
            meta = FOREX_PAIRS.get(ticker, {})
            label = pdata["label"]
            color = GREEN if pdata["change"] >= 0 else RED

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=series.index, y=series.values,
                mode="lines", name=label,
                line=dict(color="#818cf8", width=2),
                fill="tozeroy", fillcolor="rgba(129,140,248,0.06)",
            ))

            # Moving average
            ma_window = max(3, len(series) // 6)
            if len(series) > ma_window:
                ma = series.rolling(ma_window).mean()
                fig.add_trace(go.Scatter(
                    x=ma.index, y=ma.values,
                    mode="lines", name=f"{ma_window}-period MA",
                    line=dict(color="#f59e0b", width=1.5, dash="dash"),
                ))

            fig.update_layout(
                title=dict(text=label, font=dict(size=13, color="#e2e8f0")),
                height=300,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter", color="#94a3b8"),
                margin=dict(l=60, r=20, t=40, b=30),
                xaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.04)", tickformat=".4f"),
                hovermode="x unified",
                hoverlabel=dict(bgcolor="#1e1b4b", font_size=11, bordercolor="#818cf8"),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, key=f"fx_chart_{ticker}")

            # Explanation
            explain = meta.get("explain", "")
            if explain:
                st.markdown(
                    f'<div style="color:{TEXT_DIM};font-size:0.75em;margin:-8px 0 12px 0;'
                    f'padding:6px 10px;border-left:2px solid rgba(99,102,241,0.3);'
                    f'border-radius:0 6px 6px 0">{explain}</div>',
                    unsafe_allow_html=True,
                )

    # ── Trend Analysis ───────────────────────────────────────────────
    st.markdown(section_header("Trend Analysis"), unsafe_allow_html=True)
    st.markdown(
        f'<div style="color:{TEXT_DIM};font-size:0.82em;margin:-8px 0 12px 0">'
        f'Technical trend signals for each currency pair — moving average crossovers, '
        f'momentum, volatility, streaks, and support/resistance levels.</div>',
        unsafe_allow_html=True,
    )

    for ticker, pdata in pair_data.items():
        series = pdata["series"]
        label = pdata["label"]
        meta = FOREX_PAIRS.get(ticker, {})

        if len(series) < 5:
            continue

        # ── Compute trend metrics ────────────────────────────────────
        latest = float(series.iloc[-1])

        # Moving averages
        ma_short_w = max(3, len(series) // 10)
        ma_long_w = max(6, len(series) // 4)
        ma_short = series.rolling(ma_short_w).mean()
        ma_long = series.rolling(ma_long_w).mean()
        ma_short_val = float(ma_short.iloc[-1]) if not np.isnan(ma_short.iloc[-1]) else latest
        ma_long_val = float(ma_long.iloc[-1]) if len(series) >= ma_long_w and not np.isnan(ma_long.iloc[-1]) else latest

        above_short = latest > ma_short_val
        above_long = latest > ma_long_val
        short_above_long = ma_short_val > ma_long_val

        # MA signal
        if above_short and above_long and short_above_long:
            ma_signal = "Bullish"
            ma_color = GREEN
            ma_icon = "🟢"
            ma_explain = f"Price is above both short ({ma_short_w}-period) and long ({ma_long_w}-period) moving averages, and the short MA is above the long MA — a strong uptrend."
        elif not above_short and not above_long and not short_above_long:
            ma_signal = "Bearish"
            ma_color = RED
            ma_icon = "🔴"
            ma_explain = f"Price is below both moving averages, and the short MA is below the long MA — a strong downtrend."
        elif short_above_long:
            ma_signal = "Weakening Bullish"
            ma_color = YELLOW
            ma_icon = "🟡"
            ma_explain = f"Short MA is still above long MA but price is pulling back — the uptrend may be losing steam."
        else:
            ma_signal = "Weakening Bearish"
            ma_color = YELLOW
            ma_icon = "🟡"
            ma_explain = f"Short MA is below long MA but price is bouncing — the downtrend may be fading."

        # Consecutive streak
        diffs = series.diff().dropna()
        streak = 0
        if len(diffs) > 0:
            last_sign = 1 if diffs.iloc[-1] > 0 else -1
            for val in reversed(diffs.values):
                if (val > 0 and last_sign > 0) or (val < 0 and last_sign < 0):
                    streak += last_sign
                else:
                    break

        # Volatility (annualized from returns)
        returns = series.pct_change().dropna()
        if len(returns) > 5:
            daily_vol = float(returns.std())
            # Rough annualization based on interval
            ann_factor = {"5m": np.sqrt(252 * 78), "15m": np.sqrt(252 * 26),
                          "1d": np.sqrt(252), "1wk": np.sqrt(52), "1mo": np.sqrt(12)}
            vol_ann = daily_vol * ann_factor.get(interval, np.sqrt(252)) * 100
        else:
            vol_ann = 0

        # Percentile rank
        if len(series) >= 10:
            pctl = float((series < latest).sum() / len(series) * 100)
        else:
            pctl = 50.0

        # Support / resistance (period low / high)
        period_high = float(series.max())
        period_low = float(series.min())
        range_pct = ((period_high - period_low) / period_low * 100) if period_low != 0 else 0
        from_high_pct = ((latest - period_high) / period_high * 100) if period_high != 0 else 0
        from_low_pct = ((latest - period_low) / period_low * 100) if period_low != 0 else 0

        # RSI (14-period)
        rsi_val = None
        if len(returns) >= 14:
            gains = returns.clip(lower=0).rolling(14).mean()
            losses = (-returns.clip(upper=0)).rolling(14).mean()
            if losses.iloc[-1] != 0:
                rs = gains.iloc[-1] / losses.iloc[-1]
                rsi_val = 100 - (100 / (1 + rs))

        # ── Build narrative ──────────────────────────────────────────
        parts = []
        # Trend direction
        if pdata["pct_change"] > 0:
            parts.append(f"{label} has **risen {pdata['pct_change']:.2f}%** over this period.")
        elif pdata["pct_change"] < 0:
            parts.append(f"{label} has **fallen {abs(pdata['pct_change']):.2f}%** over this period.")
        else:
            parts.append(f"{label} is **flat** over this period.")

        # MA context
        parts.append(f"Trend signal: **{ma_signal}** — {ma_explain}")

        # Streak
        if abs(streak) >= 2:
            streak_dir = "consecutive gains" if streak > 0 else "consecutive declines"
            parts.append(f"Currently on a **{abs(streak)} {streak_dir}** streak.")

        # RSI
        if rsi_val is not None:
            if rsi_val > 70:
                parts.append(f"RSI at **{rsi_val:.0f}** — overbought territory, could be due for a pullback.")
            elif rsi_val < 30:
                parts.append(f"RSI at **{rsi_val:.0f}** — oversold territory, could be due for a bounce.")
            else:
                parts.append(f"RSI at **{rsi_val:.0f}** — neutral range.")

        # Position in range
        parts.append(
            f"Trading at the **{pctl:.0f}th percentile** of its range. "
            f"Period high: {period_high:.4f} ({from_high_pct:+.2f}% away), "
            f"low: {period_low:.4f} ({from_low_pct:+.2f}% above)."
        )

        narrative = " ".join(parts)

        # ── Render card ──────────────────────────────────────────────
        # Streak badge
        streak_html = ""
        if abs(streak) >= 2:
            s_arrow = "▲" if streak > 0 else "▼"
            s_color = GREEN if streak > 0 else RED
            streak_html = (
                f'<span style="color:{s_color};font-size:0.72em;font-weight:700;'
                f'padding:2px 6px;background:rgba(255,255,255,0.06);border-radius:4px;'
                f'margin-left:6px">{s_arrow}{abs(streak)} streak</span>'
            )

        # RSI badge
        rsi_html = ""
        if rsi_val is not None:
            rsi_c = RED if rsi_val > 70 else GREEN if rsi_val < 30 else TEXT_MUTED
            rsi_html = (
                f'<span style="color:{rsi_c};font-size:0.72em;font-weight:600;'
                f'padding:2px 6px;background:rgba(255,255,255,0.06);border-radius:4px;'
                f'margin-left:4px">RSI {rsi_val:.0f}</span>'
            )

        # Volatility badge
        vol_c = RED if vol_ann > 15 else YELLOW if vol_ann > 8 else GREEN
        vol_html = (
            f'<span style="color:{vol_c};font-size:0.72em;font-weight:600;'
            f'padding:2px 6px;background:rgba(255,255,255,0.06);border-radius:4px;'
            f'margin-left:4px">Vol {vol_ann:.1f}%</span>'
        )

        st.markdown(
            f'<div style="background:linear-gradient(135deg,rgba(255,255,255,0.04),rgba(255,255,255,0.015));'
            f'border:1px solid rgba(255,255,255,0.08);border-left:4px solid {ma_color};'
            f'border-radius:0 12px 12px 0;padding:16px 18px;margin-bottom:12px">'
            # Header row
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
            f'<div style="color:{TEXT_PRIMARY};font-weight:700;font-size:1em">'
            f'{ma_icon} {label}</div>'
            f'<div>{streak_html}{rsi_html}{vol_html}</div>'
            f'</div>'
            # Signal + price row
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">'
            f'<div>'
            f'<span style="color:{ma_color};font-weight:700;font-size:0.9em">{ma_signal}</span>'
            f'<span style="color:{TEXT_MUTED};font-size:0.82em;margin-left:8px">'
            f'P{pctl:.0f} of range</span>'
            f'</div>'
            f'<div style="color:{TEXT_PRIMARY};font-size:1.1em;font-weight:600">{latest:.4f}</div>'
            f'</div>'
            # Support / resistance bar
            f'<div style="display:flex;gap:12px;align-items:center;margin-bottom:10px">'
            f'<span style="color:{GREEN};font-size:0.72em">Low: {period_low:.4f}</span>'
            f'<div style="flex:1;height:6px;background:rgba(255,255,255,0.06);border-radius:3px;position:relative">'
            f'<div style="position:absolute;left:{max(1, min(99, pctl))}%;top:-3px;'
            f'width:12px;height:12px;background:{ma_color};border-radius:50%;'
            f'transform:translateX(-50%);border:2px solid rgba(0,0,0,0.3)"></div>'
            f'</div>'
            f'<span style="color:{RED};font-size:0.72em">High: {period_high:.4f}</span>'
            f'</div>'
            # Narrative
            f'<div style="color:{TEXT_SECONDARY};font-size:0.8em;line-height:1.6;'
            f'padding:10px 12px;background:rgba(255,255,255,0.02);border-radius:8px">'
            f'{narrative}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Correlation Matrix ───────────────────────────────────────────
    if len(pair_data) >= 3:
        st.markdown(section_header("Currency Correlations"), unsafe_allow_html=True)
        st.markdown(
            f'<div style="color:{TEXT_DIM};font-size:0.82em;margin:-8px 0 12px 0">'
            f'How currencies move relative to each other. '
            f'<b style="color:#3b82f6">Blue = move together</b>, '
            f'<b style="color:#ef4444">Red = move opposite</b>. '
            f'Strong correlations help you avoid doubling up on the same bet.</div>',
            unsafe_allow_html=True,
        )

        import pandas as pd
        returns = pd.DataFrame({
            FOREX_PAIRS.get(t, {}).get("label", t): pdata["series"].pct_change().dropna()
            for t, pdata in pair_data.items()
        })
        corr = returns.corr()

        if not corr.empty:
            fig = go.Figure(go.Heatmap(
                z=corr.values, x=corr.columns.tolist(), y=corr.index.tolist(),
                colorscale="RdBu_r", zmid=0, zmin=-1, zmax=1,
                text=corr.round(2).values, texttemplate="%{text}",
                textfont=dict(size=10),
            ))
            fig.update_layout(
                height=max(350, len(corr) * 50),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter", color="#94a3b8"),
                margin=dict(l=20, r=20, t=10, b=10),
                xaxis=dict(tickangle=45, tickfont=dict(size=10)),
                yaxis=dict(tickfont=dict(size=10)),
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Performance Comparison Bar ───────────────────────────────────
    if len(pair_data) >= 2:
        st.markdown(section_header("Performance Comparison"), unsafe_allow_html=True)
        st.markdown(
            f'<div style="color:{TEXT_DIM};font-size:0.82em;margin:-8px 0 12px 0">'
            f'Which currencies moved most over this period? Green = pair rose, Red = fell.</div>',
            unsafe_allow_html=True,
        )

        sorted_pairs = sorted(pair_data.items(), key=lambda x: x[1]["pct_change"])
        labels = [FOREX_PAIRS.get(t, {}).get("label", t) for t, _ in sorted_pairs]
        values = [p["pct_change"] for _, p in sorted_pairs]
        colors = [GREEN if v >= 0 else RED for v in values]

        fig = go.Figure(go.Bar(
            x=values, y=labels,
            orientation="h",
            marker=dict(color=colors),
            text=[f"{v:+.2f}%" for v in values],
            textposition="outside",
            textfont=dict(size=11, color="#e2e8f0"),
        ))
        fig.update_layout(
            height=max(250, len(labels) * 40),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color="#94a3b8"),
            margin=dict(l=20, r=80, t=10, b=30),
            xaxis=dict(tickformat=".2f", ticksuffix="%",
                       gridcolor="rgba(255,255,255,0.04)",
                       zeroline=True, zerolinecolor="rgba(255,255,255,0.15)"),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig, use_container_width=True)
