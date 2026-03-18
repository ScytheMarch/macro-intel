"""Macro variable dependency graph.

Shows causal/correlational relationships between economic indicators.
Edges derived from partial correlations or Granger-like lead-lag analysis.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from macro_intel.config.indicators import INDICATORS
from macro_intel.graphs.renderer import (
    create_network, save_network, CATEGORY_COLORS,
    edge_width_from_weight, edge_color_from_weight,
)

logger = logging.getLogger(__name__)


def build_dependency_graph(
    correlation_matrix: pd.DataFrame,
    min_correlation: float = 0.3,
    top_n_edges: int = 50,
    output_path: str | Path | None = None,
) -> str:
    """Build macro variable dependency graph from correlation matrix.

    Args:
        correlation_matrix: Square DataFrame of indicator correlations
        min_correlation: Minimum absolute correlation to show an edge
        top_n_edges: Maximum number of edges to display (strongest)
        output_path: Where to save HTML

    Returns:
        Path to saved HTML file.
    """
    net = create_network(title="Macro Dependency Graph")

    indicators = list(correlation_matrix.columns)

    # ── Add indicator nodes ──────────────────────────────────────────────
    for sid in indicators:
        ind = INDICATORS.get(sid)
        if ind:
            label = ind.name
            category = ind.category
            color = CATEGORY_COLORS.get(category, "#64748b")
            title_text = (
                f"<b>{ind.name}</b><br>"
                f"Category: {category}<br>"
                f"Source: {ind.source}<br>"
                f"Frequency: {ind.frequency}"
            )
        else:
            label = sid
            color = "#64748b"
            title_text = sid
            category = "Unknown"

        net.add_node(
            sid,
            label=label,
            title=title_text,
            color=color,
            size=18,
            shape="dot",
            group=category if ind else "Unknown",
        )

    # ── Collect and rank edges ───────────────────────────────────────────
    edges = []
    for i, s1 in enumerate(indicators):
        for s2 in indicators[i + 1:]:
            corr = float(correlation_matrix.loc[s1, s2])
            if abs(corr) >= min_correlation:
                edges.append((s1, s2, corr))

    # Sort by absolute correlation, take top N
    edges.sort(key=lambda x: abs(x[2]), reverse=True)
    edges = edges[:top_n_edges]

    # ── Add edges ────────────────────────────────────────────────────────
    for s1, s2, corr in edges:
        net.add_edge(
            s1, s2,
            value=abs(corr),
            width=edge_width_from_weight(abs(corr)),
            color=edge_color_from_weight(corr),
            title=f"{s1} ↔ {s2}: {corr:+.3f}",
        )

    # ── Save ─────────────────────────────────────────────────────────────
    if output_path is None:
        from macro_intel.config.settings import settings
        output_path = settings.reports_dir / "macro_dependency.html"

    return save_network(net, output_path, title="🔗 Macro Variable Dependencies")


def compute_lead_lag_matrix(
    panel: pd.DataFrame,
    country: str = "USA",
    max_lag: int = 6,
    features: list[str] | None = None,
) -> pd.DataFrame:
    """Compute lead-lag relationships between indicators.

    For each pair (A, B), computes the lag at which cross-correlation is maximized.
    Positive lag = A leads B.

    Returns DataFrame with columns: indicator_1, indicator_2, best_lag, max_corr
    """
    try:
        data = panel.xs(country, level="country")
    except KeyError:
        return pd.DataFrame()

    if features:
        data = data[[c for c in features if c in data.columns]]

    cols = list(data.columns)
    results = []

    for i, c1 in enumerate(cols):
        s1 = data[c1].dropna()
        for c2 in cols[i + 1:]:
            s2 = data[c2].dropna()

            # Align
            aligned = pd.concat([s1, s2], axis=1).dropna()
            if len(aligned) < max_lag + 6:
                continue

            best_lag = 0
            best_corr = 0.0

            for lag in range(-max_lag, max_lag + 1):
                if lag >= 0:
                    corr = aligned.iloc[lag:, 0].corr(aligned.iloc[:len(aligned) - lag if lag > 0 else len(aligned), 1])
                else:
                    corr = aligned.iloc[:lag, 0].corr(aligned.iloc[-lag:, 1])

                if pd.notna(corr) and abs(corr) > abs(best_corr):
                    best_corr = corr
                    best_lag = lag

            if abs(best_corr) > 0.2:
                results.append({
                    "indicator_1": c1,
                    "indicator_2": c2,
                    "best_lag": best_lag,
                    "max_corr": round(best_corr, 3),
                    "relationship": (
                        f"{c1} leads {c2} by {best_lag}m" if best_lag > 0
                        else f"{c2} leads {c1} by {-best_lag}m" if best_lag < 0
                        else "contemporaneous"
                    ),
                })

    return pd.DataFrame(results).sort_values("max_corr", key=abs, ascending=False)
