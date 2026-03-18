"""Tests for the feature panel assembler and data cache."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from macro_intel.data.feature_panel import (
    PanelConfig,
    build_panel,
    standardize_panel,
    get_panel_summary,
    align_frequencies,
)
from macro_intel.data import cache


class TestCache:
    """SQLite cache CRUD operations."""

    def test_init_db(self):
        """init_db creates tables without error."""
        cache.init_db()

    def test_upsert_and_get_observations(self):
        cache.init_db()
        dates = pd.date_range("2023-01-01", periods=12, freq="ME")
        df = pd.DataFrame({"value": range(12)}, index=dates)
        n = cache.upsert_observations("TEST_SERIES", df, country="USA")
        assert n == 12

        result = cache.get_observations("TEST_SERIES", "USA")
        assert len(result) == 12
        assert "value" in result.columns

    def test_get_observations_with_start_date(self):
        cache.init_db()
        dates = pd.date_range("2023-01-01", periods=12, freq="ME")
        df = pd.DataFrame({"value": range(12)}, index=dates)
        cache.upsert_observations("TEST2", df, country="USA")

        result = cache.get_observations("TEST2", "USA", start_date="2023-07-01")
        assert len(result) <= 6

    def test_upsert_metadata(self):
        cache.init_db()
        cache.upsert_metadata("GDP", country="USA", source="fred", title="Real GDP")
        meta = cache.get_metadata("GDP", "USA")
        assert meta is not None
        assert meta["title"] == "Real GDP"

    def test_is_stale_returns_true_for_missing(self):
        cache.init_db()
        assert cache.is_stale("NONEXISTENT", "USA") is True

    def test_log_model_run(self):
        cache.init_db()
        run_id = cache.log_model_run(
            model_type="regime_hmm",
            countries=["USA"],
            n_features=10,
            n_regimes=4,
            draws=100,
            artifact="/tmp/test.nc",
        )
        assert run_id > 0

        run = cache.get_latest_model_run("regime_hmm")
        assert run is not None
        assert run["n_regimes"] == 4

    def test_get_latest(self):
        cache.init_db()
        dates = pd.date_range("2023-01-01", periods=5, freq="ME")
        df = pd.DataFrame({"value": [10, 20, 30, 40, 50]}, index=dates)
        cache.upsert_observations("LATEST_TEST", df)

        d, v = cache.get_latest("LATEST_TEST")
        assert v == 50

    def test_empty_observations(self):
        cache.init_db()
        result = cache.get_observations("DOES_NOT_EXIST", "USA")
        assert result.empty


class TestPanelConfig:
    def test_defaults(self):
        cfg = PanelConfig()
        assert cfg.countries == ["USA"]
        assert cfg.frequency == "M"
        assert cfg.start_date == "2000-01-01"


class TestBuildPanel:
    def test_build_empty_panel_no_cache(self):
        """build_panel returns empty DataFrame when cache has nothing."""
        cache.init_db()
        panel = build_panel(PanelConfig(countries=["USA"], fred_indicators=[], wb_indicators=[],
                                         include_market_returns=False))
        assert panel.empty

    def test_build_with_cached_data(self):
        """build_panel picks up data from cache."""
        cache.init_db()
        dates = pd.date_range("2020-01-01", periods=36, freq="ME")
        for sid in ["CPIAUCSL", "UNRATE"]:
            df = pd.DataFrame({"value": np.random.randn(36) + 3}, index=dates)
            cache.upsert_observations(sid, df, country="USA")

        panel = build_panel(PanelConfig(
            countries=["USA"],
            fred_indicators=["CPIAUCSL", "UNRATE"],
            wb_indicators=[],
            include_market_returns=False,
        ))
        assert not panel.empty
        assert "CPIAUCSL" in panel.columns
        assert "UNRATE" in panel.columns


class TestStandardizePanel:
    def test_z_scores_have_zero_mean(self, sample_panel):
        std_panel = standardize_panel(sample_panel)
        usa = std_panel.xs("USA", level="country")
        # Z-scored columns should have mean ≈ 0
        for col in usa.columns:
            assert abs(usa[col].mean()) < 0.1, f"{col} mean not near 0"

    def test_empty_panel(self):
        empty = pd.DataFrame()
        result = standardize_panel(empty)
        assert result.empty


class TestPanelSummary:
    def test_summary_fields(self, sample_panel):
        summary = get_panel_summary(sample_panel)
        assert summary["n_rows"] == 120  # 60 dates * 2 countries
        assert summary["n_features"] == 6
        assert set(summary["countries"]) == {"USA", "GBR"}
        assert summary["date_range"] is not None
        assert "missing_pct" in summary

    def test_empty_summary(self):
        summary = get_panel_summary(pd.DataFrame())
        assert summary["n_rows"] == 0
        assert summary["countries"] == []


class TestAlignFrequencies:
    def test_align_preserves_countries(self, sample_panel):
        aligned = align_frequencies(sample_panel, freq="M")
        countries = aligned.index.get_level_values("country").unique()
        assert set(countries) == {"USA", "GBR"}

    def test_empty_panel(self):
        result = align_frequencies(pd.DataFrame())
        assert result.empty
