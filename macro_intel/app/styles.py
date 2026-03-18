"""Design tokens, styling utilities, and glass-card components for Macro-Intel."""

# Traffic light colors
GREEN = "#22c55e"
YELLOW = "#eab308"
RED = "#ef4444"
GRAY = "#6b7280"
BLUE = "#3b82f6"
DARK_BG = "#0e1117"

# Text hierarchy
TEXT_PRIMARY = "#f1f5f9"
TEXT_SECONDARY = "#94a3b8"
TEXT_MUTED = "#64748b"
TEXT_DIM = "#475569"

# Accents
ACCENT_INDIGO = "#6366f1"
ACCENT_VIOLET = "#8b5cf6"

# Card tokens
CARD_BG = "linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015))"
CARD_BORDER = "1px solid rgba(255,255,255,0.08)"
CARD_RADIUS = "12px"
CARD_PADDING = "14px 18px"

# Category colors
CATEGORY_COLORS = {
    "Inflation": "#f97316",
    "Labor": "#3b82f6",
    "Output": "#8b5cf6",
    "Consumer": "#06b6d4",
    "Business": "#ec4899",
    "Housing": "#84cc16",
    "Trade": "#14b8a6",
    "Monetary": "#f59e0b",
    "Fiscal": "#ec4899",
    "Fixed Income": "#6366f1",
    "Market": "#ef4444",
    "Structural": "#64748b",
    "Regime": "#6b7280",
}

# Regime colors
REGIME_COLORS = {
    "Expansion": "#22c55e",
    "Slowdown": "#eab308",
    "Contraction": "#ef4444",
    "Crisis": "#dc2626",
    "Unknown": "#6b7280",
}


def glass_card(content: str, border_color: str = "rgba(255,255,255,0.08)",
               padding: str = CARD_PADDING) -> str:
    return (
        f'<div style="background:{CARD_BG};border:1px solid {border_color};'
        f'border-radius:{CARD_RADIUS};padding:{padding};'
        f'backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);'
        f'box-shadow:0 2px 8px rgba(0,0,0,0.15)">{content}</div>'
    )


def section_header(text: str) -> str:
    return (
        f'<div style="color:{TEXT_MUTED};font-size:0.75em;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:1.5px;'
        f'margin:20px 0 12px 0">{text}</div>'
    )


def badge(text: str, color: str, bg_opacity: float = 0.15) -> str:
    return (
        f'<span style="background:rgba({_hex_to_rgb(color)},{bg_opacity});'
        f'color:{color};padding:2px 8px;border-radius:6px;font-size:0.72em;'
        f'font-weight:600;letter-spacing:0.3px">{text}</span>'
    )


def metric_card(label: str, value: str, color: str = TEXT_PRIMARY,
                sublabel: str = "", border_left: str = "") -> str:
    border = f"border-left:4px solid {border_left};" if border_left else ""
    sub = f'<div style="color:{TEXT_MUTED};font-size:0.7em;margin-top:4px">{sublabel}</div>' if sublabel else ""
    return (
        f'<div style="background:{CARD_BG};border:1px solid rgba(255,255,255,0.08);'
        f'border-radius:{CARD_RADIUS};padding:16px 20px;{border}'
        f'backdrop-filter:blur(8px)">'
        f'<div style="color:{TEXT_MUTED};font-size:0.7em;text-transform:uppercase;'
        f'letter-spacing:1.2px;font-weight:600">{label}</div>'
        f'<div style="color:{color};font-size:1.8em;font-weight:700;margin-top:4px">{value}</div>'
        f'{sub}</div>'
    )


def trend_color(direction: str, higher_is: str) -> str:
    if higher_is in ("contractionary", "inflationary"):
        flipped = {"improving": "deteriorating", "deteriorating": "improving", "stable": "stable"}
        direction = flipped.get(direction, direction)
    return {"improving": GREEN, "stable": YELLOW, "deteriorating": RED}.get(direction, GRAY)


def trend_arrow(direction: str, higher_is: str) -> str:
    if higher_is in ("contractionary", "inflationary"):
        flipped = {"improving": "deteriorating", "deteriorating": "improving", "stable": "stable"}
        direction = flipped.get(direction, direction)
    return {"improving": "▲", "stable": "▬", "deteriorating": "▼"}.get(direction, "▬")


def z_color(z: float) -> str:
    """Map z-score magnitude to traffic-light color."""
    az = abs(z)
    if az < 1.0:
        return GREEN
    elif az < 2.0:
        return YELLOW
    else:
        return RED


def format_value(value: float | None, unit: str = "", transform: str = "") -> str:
    if value is None:
        return "N/A"
    if transform in ("yoy_pct", "mom_pct", "annualized"):
        return f"{value:+.1f}%"
    if unit == "percent":
        return f"{value:.1f}%"
    if unit == "index":
        return f"{value:.1f}"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{value:,.0f}"
    return f"{value:.2f}"


def _hex_to_rgb(hex_color: str) -> str:
    """Convert #RRGGBB to r,g,b string."""
    h = hex_color.lstrip("#")
    return ",".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))


# ── Global CSS for premium glass theme ────────────────────────────────────────

GLOBAL_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    .stApp {
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        background:
            radial-gradient(ellipse 60% 50% at 15% 10%, rgba(99,102,241,0.06), transparent),
            radial-gradient(ellipse 50% 40% at 85% 80%, rgba(139,92,246,0.04), transparent),
            #0e1117;
    }

    /* Frosted glass metric cards */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 14px 18px;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
        transition: all 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        border-color: rgba(99,102,241,0.25);
        background: linear-gradient(135deg, rgba(99,102,241,0.08), rgba(255,255,255,0.02));
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(99,102,241,0.1);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.7em !important;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: #64748b !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8em !important;
        font-weight: 700 !important;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        color: #94a3b8;
        font-weight: 500;
        padding: 8px 20px;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(99,102,241,0.12), rgba(99,102,241,0.06));
        border-color: rgba(99,102,241,0.3);
        color: #c7d2fe;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1, #7c3aed, #8b5cf6) !important;
        border: 1px solid rgba(129,140,248,0.4) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        box-shadow: 0 0 20px rgba(99,102,241,0.25);
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 0 30px rgba(99,102,241,0.4);
    }

    /* Selectbox, inputs */
    [data-testid="stSelectbox"] > div > div,
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 10px !important;
        backdrop-filter: blur(8px);
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 4px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 0.85em;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(99,102,241,0.15) !important;
        box-shadow: 0 0 10px rgba(99,102,241,0.1);
    }

    /* Chart containers */
    [data-testid="stPlotlyChart"] {
        background: linear-gradient(135deg, rgba(255,255,255,0.02), rgba(255,255,255,0.008));
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 8px;
        backdrop-filter: blur(8px);
        box-shadow: 0 2px 10px rgba(0,0,0,0.15);
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px;
        font-weight: 600;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.2); border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,0.4); }

    /* Alert styling */
    .stAlert { border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); backdrop-filter: blur(12px); }

    /* Progress bar */
    .stProgress > div > div { background: linear-gradient(90deg, #6366f1, #8b5cf6, #a78bfa); border-radius: 10px; }

    /* Dataframe */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
    }

    /* Divider */
    hr { border-color: rgba(255,255,255,0.06) !important; }

    /* Radio buttons (sidebar nav) */
    .stRadio > div { gap: 2px; }
</style>
"""
