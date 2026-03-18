"""Portfolio exposure network graph.

Bipartite graph: holdings → countries → sectors → factors.
Shows hidden concentration and cross-exposure relationships.
"""

from __future__ import annotations

import logging
from pathlib import Path

from macro_intel.graphs.renderer import (
    create_network, save_network, NODE_COLORS, edge_width_from_weight,
)

logger = logging.getLogger(__name__)


def build_portfolio_network(
    holdings: dict[str, float],
    country_map: dict[str, str] | None = None,
    sector_map: dict[str, str] | None = None,
    factor_exposures: dict[str, dict[str, float]] | None = None,
    output_path: str | Path | None = None,
) -> str:
    """Build interactive portfolio exposure network.

    Args:
        holdings: Dict mapping ticker -> weight (0-1)
        country_map: Dict mapping ticker -> country ISO3
        sector_map: Dict mapping ticker -> sector name
        factor_exposures: Dict mapping ticker -> {factor_name: loading}
        output_path: Where to save HTML

    Returns:
        Path to saved HTML file.
    """
    net = create_network(title="Portfolio Exposure Network", directed=True)

    # ── Holding nodes ────────────────────────────────────────────────────
    for ticker, weight in holdings.items():
        size = max(10, min(40, weight * 100))
        net.add_node(
            f"H_{ticker}",
            label=f"{ticker}\n{weight:.1%}",
            title=f"<b>{ticker}</b><br>Weight: {weight:.2%}",
            color=NODE_COLORS["holding"],
            size=size,
            shape="dot",
            group="holdings",
        )

    # ── Country nodes + edges ────────────────────────────────────────────
    if country_map:
        country_weights: dict[str, float] = {}
        for ticker, country in country_map.items():
            if ticker in holdings:
                country_weights[country] = country_weights.get(country, 0) + holdings[ticker]

        for country, total_weight in country_weights.items():
            net.add_node(
                f"C_{country}",
                label=country,
                title=f"<b>{country}</b><br>Total exposure: {total_weight:.1%}",
                color=NODE_COLORS["country"],
                size=max(15, min(45, total_weight * 120)),
                shape="diamond",
                group="countries",
            )

        for ticker, country in country_map.items():
            if ticker in holdings:
                net.add_edge(
                    f"H_{ticker}", f"C_{country}",
                    width=edge_width_from_weight(holdings[ticker], max_w=5),
                    color="rgba(99,102,241,0.3)",
                    title=f"{ticker} → {country}: {holdings[ticker]:.1%}",
                )

    # ── Sector nodes + edges ─────────────────────────────────────────────
    if sector_map:
        sector_weights: dict[str, float] = {}
        for ticker, sector in sector_map.items():
            if ticker in holdings:
                sector_weights[sector] = sector_weights.get(sector, 0) + holdings[ticker]

        for sector, total_weight in sector_weights.items():
            net.add_node(
                f"S_{sector}",
                label=sector,
                title=f"<b>{sector}</b><br>Total exposure: {total_weight:.1%}",
                color=NODE_COLORS["sector"],
                size=max(12, min(40, total_weight * 100)),
                shape="triangle",
                group="sectors",
            )

        for ticker, sector in sector_map.items():
            if ticker in holdings:
                net.add_edge(
                    f"H_{ticker}", f"S_{sector}",
                    width=edge_width_from_weight(holdings[ticker], max_w=4),
                    color="rgba(167,139,250,0.25)",
                    title=f"{ticker} → {sector}: {holdings[ticker]:.1%}",
                )

    # ── Factor nodes + edges ─────────────────────────────────────────────
    if factor_exposures:
        all_factors: set[str] = set()
        for factors in factor_exposures.values():
            all_factors.update(factors.keys())

        for factor in all_factors:
            net.add_node(
                f"F_{factor}",
                label=factor,
                title=f"<b>Factor: {factor}</b>",
                color=NODE_COLORS["factor"],
                size=18,
                shape="square",
                group="factors",
            )

        for ticker, factors in factor_exposures.items():
            if ticker not in holdings:
                continue
            for factor, loading in factors.items():
                if abs(loading) < 0.1:
                    continue
                color = "rgba(34,197,94,0.3)" if loading > 0 else "rgba(239,68,68,0.3)"
                net.add_edge(
                    f"H_{ticker}", f"F_{factor}",
                    width=edge_width_from_weight(abs(loading), max_w=4),
                    color=color,
                    title=f"{ticker} → {factor}: {loading:.2f}",
                )

    # ── Save ─────────────────────────────────────────────────────────────
    if output_path is None:
        from macro_intel.config.settings import settings
        output_path = settings.reports_dir / "portfolio_network.html"

    return save_network(net, output_path, title="💼 Portfolio Exposure Network")
