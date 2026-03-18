"""PyVis rendering utilities — shared styling and export helpers."""

from __future__ import annotations

from pathlib import Path

from pyvis.network import Network


# ── Color palette ────────────────────────────────────────────────────────────
REGIME_COLORS = {
    "Expansion": "#22c55e",
    "Slowdown": "#eab308",
    "Stagflation": "#f97316",
    "Crisis": "#ef4444",
    "Unknown": "#64748b",
}

CATEGORY_COLORS = {
    "Inflation": "#ef4444",
    "Labor": "#3b82f6",
    "Output": "#22c55e",
    "Consumer": "#a855f7",
    "Business": "#f97316",
    "Housing": "#06b6d4",
    "Trade": "#eab308",
    "Monetary": "#8b5cf6",
    "Fiscal": "#ec4899",
    "Fixed Income": "#6366f1",
    "Market": "#14b8a6",
    "Structural": "#64748b",
}

NODE_COLORS = {
    "country": "#818cf8",
    "sector": "#a78bfa",
    "factor": "#c084fc",
    "holding": "#60a5fa",
    "indicator": "#34d399",
}


def create_network(
    title: str = "Macro Intel Network",
    height: str = "700px",
    width: str = "100%",
    directed: bool = False,
    dark_mode: bool = True,
) -> Network:
    """Create a styled PyVis network with consistent look."""
    net = Network(
        height=height,
        width=width,
        directed=directed,
        notebook=False,
        cdn_resources="remote",
    )

    # Physics settings for readable layout
    net.set_options("""
    {
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.005,
                "springLength": 150,
                "springConstant": 0.08,
                "damping": 0.4
            },
            "solver": "forceAtlas2Based",
            "stabilization": {
                "enabled": true,
                "iterations": 200
            }
        },
        "nodes": {
            "font": {
                "color": "#e2e8f0",
                "size": 14
            },
            "borderWidth": 2,
            "borderWidthSelected": 3
        },
        "edges": {
            "color": {
                "inherit": false,
                "color": "rgba(148,163,184,0.3)"
            },
            "smooth": {
                "type": "continuous"
            }
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 100,
            "navigationButtons": true
        }
    }
    """)

    return net


def save_network(net: Network, path: str | Path, title: str = "") -> str:
    """Save network to HTML file with dark-mode styling.

    Returns the file path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    net.save_graph(str(path))

    # Inject dark-mode CSS
    html = path.read_text(encoding="utf-8")
    dark_css = """
    <style>
        body { background-color: #0f172a; margin: 0; }
        #mynetwork { border: 1px solid rgba(99,102,241,0.2); border-radius: 12px; }
        .vis-network { background-color: #0f172a !important; }
    </style>
    """
    if title:
        title_html = (
            f'<div style="background:#0f172a;color:#e2e8f0;padding:12px 20px;'
            f'font-family:system-ui;font-size:1.1em;font-weight:600;'
            f'letter-spacing:-0.3px">{title}</div>'
        )
        html = html.replace("<body>", f"<body>{dark_css}{title_html}", 1)
    else:
        html = html.replace("<body>", f"<body>{dark_css}", 1)

    path.write_text(html, encoding="utf-8")
    return str(path)


def edge_width_from_weight(weight: float, min_w: float = 1.0, max_w: float = 8.0) -> float:
    """Map a weight (0-1) to an edge width."""
    return min_w + abs(weight) * (max_w - min_w)


def edge_color_from_weight(weight: float) -> str:
    """Color edge by sign and magnitude."""
    if weight > 0.5:
        return "rgba(34,197,94,0.6)"   # Strong positive = green
    elif weight > 0.2:
        return "rgba(34,197,94,0.3)"   # Weak positive = faint green
    elif weight > -0.2:
        return "rgba(148,163,184,0.2)" # Near zero = gray
    elif weight > -0.5:
        return "rgba(239,68,68,0.3)"   # Weak negative = faint red
    else:
        return "rgba(239,68,68,0.6)"   # Strong negative = red
