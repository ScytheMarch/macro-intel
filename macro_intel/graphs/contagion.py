"""Country contagion / similarity network.

Nodes = countries, edges weighted by correlation, regime similarity,
or trade linkage.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from macro_intel.config.countries import COUNTRIES
from macro_intel.graphs.renderer import (
    create_network, save_network,
    REGIME_COLORS, edge_width_from_weight, edge_color_from_weight,
)

logger = logging.getLogger(__name__)


def build_contagion_network(
    similarity_matrix: pd.DataFrame,
    regime_labels: dict[str, str] | None = None,
    min_edge_weight: float = 0.2,
    output_path: str | Path | None = None,
) -> str:
    """Build an interactive country contagion/similarity network.

    Args:
        similarity_matrix: Square DataFrame (countries x countries) with similarity scores
        regime_labels: Dict mapping country ISO3 -> current regime label
        min_edge_weight: Minimum absolute weight to show an edge
        output_path: Where to save the HTML file

    Returns:
        Path to saved HTML file.
    """
    if regime_labels is None:
        regime_labels = {}

    net = create_network(title="Country Contagion Network")
    countries = list(similarity_matrix.columns)

    # ── Add country nodes ────────────────────────────────────────────────
    for country in countries:
        c_info = COUNTRIES.get(country)
        label = c_info.name if c_info else country
        regime = regime_labels.get(country, "Unknown")
        color = REGIME_COLORS.get(regime, "#64748b")

        net.add_node(
            country,
            label=f"{label}\n({regime})",
            title=f"<b>{label}</b><br>Regime: {regime}<br>Currency: {c_info.currency if c_info else '?'}",
            color=color,
            size=25,
            shape="dot",
            font={"size": 12, "color": "#e2e8f0"},
        )

    # ── Add edges ────────────────────────────────────────────────────────
    for i, c1 in enumerate(countries):
        for c2 in countries[i + 1:]:
            weight = float(similarity_matrix.loc[c1, c2])
            if abs(weight) < min_edge_weight:
                continue

            net.add_edge(
                c1, c2,
                value=abs(weight),
                width=edge_width_from_weight(weight),
                color=edge_color_from_weight(weight),
                title=f"{c1} ↔ {c2}: {weight:.3f}",
            )

    # ── Save ─────────────────────────────────────────────────────────────
    if output_path is None:
        from macro_intel.config.settings import settings
        output_path = settings.reports_dir / "contagion_network.html"

    return save_network(net, output_path, title="🌐 Country Contagion Network")


def build_regime_similarity_matrix(
    regime_probs: dict[str, np.ndarray],
) -> pd.DataFrame:
    """Build similarity matrix from posterior regime probabilities.

    Uses Jensen-Shannon divergence (inverted to similarity).

    Args:
        regime_probs: Dict mapping country -> array of shape (T, K) regime probabilities

    Returns:
        Square similarity DataFrame.
    """
    from scipy.spatial.distance import jensenshannon

    countries = list(regime_probs.keys())
    n = len(countries)
    sim = pd.DataFrame(1.0, index=countries, columns=countries)

    for i, c1 in enumerate(countries):
        p1 = regime_probs[c1]
        for c2 in countries[i + 1:]:
            p2 = regime_probs[c2]

            # Align lengths
            min_len = min(len(p1), len(p2))
            p1_aligned = p1[-min_len:]
            p2_aligned = p2[-min_len:]

            # Average JSD across time steps
            jsds = []
            for t in range(min_len):
                jsd = jensenshannon(p1_aligned[t], p2_aligned[t])
                if not np.isnan(jsd):
                    jsds.append(jsd)

            avg_jsd = float(np.mean(jsds)) if jsds else 1.0
            similarity = 1.0 - avg_jsd  # Invert: 1 = identical, 0 = maximally different

            sim.loc[c1, c2] = sim.loc[c2, c1] = similarity

    return sim
