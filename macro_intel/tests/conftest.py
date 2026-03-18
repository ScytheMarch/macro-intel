"""Shared fixtures for macro-intel tests."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def _isolate_env(tmp_path, monkeypatch):
    """Point all IO to temp dirs so tests never touch real data."""
    monkeypatch.setenv("MACRO_INTEL_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("MACRO_INTEL_MODEL_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("MACRO_INTEL_REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("FRED_API_KEY", "test_key_not_real")


@pytest.fixture
def sample_panel() -> pd.DataFrame:
    """Build a small MultiIndex (date, country) panel for testing."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-31", periods=60, freq="ME")
    countries = ["USA", "GBR"]
    rows = []
    for country in countries:
        for i, d in enumerate(dates):
            rows.append({
                "date": d,
                "country": country,
                "CPIAUCSL": 2.0 + np.random.randn() * 0.5 + (0.3 if country == "GBR" else 0),
                "UNRATE": 4.0 + np.random.randn() * 0.3,
                "GDPC1": 2.5 + np.random.randn() * 1.0,
                "INDPRO": 100 + np.random.randn() * 3,
                "FEDFUNDS": 1.5 + np.random.randn() * 0.5,
                "EQUITY_RETURN": np.random.randn() * 3,
            })
    df = pd.DataFrame(rows)
    df = df.set_index(["date", "country"]).sort_index()
    return df


@pytest.fixture
def single_country_panel(sample_panel) -> pd.DataFrame:
    """USA-only slice of the sample panel."""
    return sample_panel.xs("USA", level="country").copy().assign(country="USA").reset_index().set_index(["date", "country"])


@pytest.fixture
def sample_similarity_matrix() -> pd.DataFrame:
    """Small similarity matrix for graph tests."""
    countries = ["USA", "GBR", "DEU"]
    data = np.array([
        [1.0, 0.7, 0.4],
        [0.7, 1.0, 0.8],
        [0.4, 0.8, 1.0],
    ])
    return pd.DataFrame(data, index=countries, columns=countries)


@pytest.fixture
def sample_regime_result():
    """Minimal RegimeResult-like object for bridge/analog tests."""
    from macro_intel.models.regime_hmm import RegimeResult

    T, K = 60, 4
    np.random.seed(42)

    # Generate valid regime probabilities (rows sum to 1)
    raw = np.random.dirichlet([2, 1, 1, 0.5], size=T)
    dates = pd.date_range("2020-01-31", periods=T, freq="ME")

    return RegimeResult(
        regime_probs=raw,
        regime_hdi=np.stack([raw * 0.85, np.minimum(raw * 1.15, 1.0)], axis=-1),
        regime_map=np.argmax(raw, axis=1),
        regime_labels=["Expansion", "Slowdown", "Stagflation", "Crisis"],
        transition_matrix=np.array([
            [0.8, 0.1, 0.05, 0.05],
            [0.15, 0.7, 0.1, 0.05],
            [0.1, 0.15, 0.65, 0.1],
            [0.2, 0.1, 0.1, 0.6],
        ]),
        regime_means=np.random.randn(K, 6),
        feature_names=["CPIAUCSL", "UNRATE", "GDPC1", "INDPRO", "FEDFUNDS", "EQUITY_RETURN"],
        countries=["USA"],
        dates=dates,
        uncertainty=0.35,
    )
