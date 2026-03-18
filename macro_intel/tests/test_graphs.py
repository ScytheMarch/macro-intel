"""Tests for network graph generation."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from macro_intel.graphs.renderer import (
    create_network,
    save_network,
    edge_width_from_weight,
    edge_color_from_weight,
    REGIME_COLORS,
    CATEGORY_COLORS,
    NODE_COLORS,
)
from macro_intel.graphs.contagion import (
    build_contagion_network,
    build_regime_similarity_matrix,
)


class TestRenderer:
    def test_create_network(self):
        net = create_network(title="Test")
        assert net is not None

    def test_save_network(self, tmp_path):
        net = create_network()
        net.add_node("A", label="A", color="#ff0000")
        net.add_node("B", label="B", color="#00ff00")
        net.add_edge("A", "B")
        path = save_network(net, tmp_path / "test.html", title="Test Graph")
        assert Path(path).exists()
        html = Path(path).read_text()
        assert "Test Graph" in html
        assert "background-color: #0f172a" in html

    def test_edge_width_from_weight(self):
        assert edge_width_from_weight(0.0) == 1.0
        assert edge_width_from_weight(1.0) == 8.0
        assert 1.0 < edge_width_from_weight(0.5) < 8.0

    def test_edge_color_from_weight(self):
        green = edge_color_from_weight(0.8)
        assert "34,197,94" in green  # Green
        red = edge_color_from_weight(-0.8)
        assert "239,68,68" in red  # Red
        gray = edge_color_from_weight(0.0)
        assert "148,163,184" in gray  # Gray

    def test_color_palettes(self):
        assert len(REGIME_COLORS) >= 4
        assert "Expansion" in REGIME_COLORS
        assert "Crisis" in REGIME_COLORS
        assert len(CATEGORY_COLORS) >= 10
        assert len(NODE_COLORS) >= 4


class TestContagionNetwork:
    def test_build_contagion_network(self, sample_similarity_matrix, tmp_path):
        path = build_contagion_network(
            sample_similarity_matrix,
            regime_labels={"USA": "Expansion", "GBR": "Slowdown", "DEU": "Crisis"},
            output_path=tmp_path / "contagion.html",
        )
        assert Path(path).exists()
        html = Path(path).read_text()
        assert len(html) > 100

    def test_build_without_regime_labels(self, sample_similarity_matrix, tmp_path):
        path = build_contagion_network(
            sample_similarity_matrix,
            output_path=tmp_path / "contagion2.html",
        )
        assert Path(path).exists()


class TestRegimeSimilarityMatrix:
    def test_basic(self):
        T, K = 30, 4
        np.random.seed(42)
        probs = {
            "USA": np.random.dirichlet([3, 1, 1, 0.5], size=T),
            "GBR": np.random.dirichlet([2, 2, 1, 0.5], size=T),
            "DEU": np.random.dirichlet([1, 1, 3, 1], size=T),
        }
        sim = build_regime_similarity_matrix(probs)
        assert sim.shape == (3, 3)
        # Diagonal should be 1.0
        np.testing.assert_allclose(np.diag(sim.values), 1.0)
        # Symmetric
        np.testing.assert_allclose(sim.values, sim.values.T, atol=1e-10)
        # Values between 0 and 1
        assert (sim.values >= 0).all()
        assert (sim.values <= 1.0 + 1e-6).all()
