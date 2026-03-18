"""Tests for portfolio bridge components."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from macro_intel.bridge.exposure_mapper import (
    resolve_country,
    resolve_sector,
    _ETF_COUNTRY_MAP,
    _ETF_SECTOR_MAP,
)
from macro_intel.bridge.analog import AnalogPeriod, find_analogs


class TestExposureMapper:
    def test_known_etf_country(self):
        assert resolve_country("SPY") == "USA"
        assert resolve_country("EWJ") == "JPN"
        assert resolve_country("FXI") == "CHN"
        assert resolve_country("VXUS") == "INTL"

    def test_unknown_ticker_defaults_usa(self):
        """Unknown ticker without yfinance should default to USA."""
        result = resolve_country("ZZZZZZ_FAKE")
        assert result == "USA"

    def test_known_etf_sector(self):
        assert resolve_sector("XLK") == "Technology"
        assert resolve_sector("BND") == "Fixed Income"
        assert resolve_sector("GLD") == "Commodities"

    def test_unknown_sector_defaults(self):
        result = resolve_sector("ZZZZZZ_FAKE")
        assert result == "Unknown"

    def test_etf_country_map_completeness(self):
        """All common US ETFs should be in the map."""
        common = ["SPY", "QQQ", "IWM", "BND", "GLD"]
        for t in common:
            assert t in _ETF_COUNTRY_MAP

    def test_etf_sector_map_completeness(self):
        spdr_sectors = ["XLK", "XLF", "XLV", "XLE", "XLI", "XLP", "XLY", "XLU", "XLRE", "XLC", "XLB"]
        for t in spdr_sectors:
            assert t in _ETF_SECTOR_MAP


class TestAnalogPeriod:
    def test_construction(self):
        a = AnalogPeriod(
            start_date="2020-01-31",
            end_date="2020-06-30",
            similarity_score=0.85,
            regime_label="Expansion",
            duration_months=6,
            forward_return_6m=0.05,
            forward_return_12m=0.12,
        )
        assert a.similarity_score == 0.85
        assert a.regime_label == "Expansion"


class TestFindAnalogs:
    def test_find_analogs_basic(self, sample_regime_result, sample_panel):
        analogs = find_analogs(
            sample_regime_result,
            sample_panel,
            country="USA",
            n_analogs=3,
            lookback_window=6,
        )
        # Should return up to 3
        assert len(analogs) <= 3
        for a in analogs:
            assert isinstance(a, AnalogPeriod)
            assert 0 <= a.similarity_score <= 1.0
            assert a.duration_months == 6

    def test_no_overlap(self, sample_regime_result, sample_panel):
        analogs = find_analogs(
            sample_regime_result,
            sample_panel,
            country="USA",
            n_analogs=5,
            lookback_window=6,
        )
        # Verify no overlapping windows
        for i, a1 in enumerate(analogs):
            for a2 in analogs[i + 1:]:
                assert a1.start_date != a2.start_date

    def test_insufficient_data(self, sample_regime_result, sample_panel):
        """With large lookback window, should return empty or fewer results."""
        analogs = find_analogs(
            sample_regime_result,
            sample_panel,
            country="USA",
            n_analogs=5,
            lookback_window=50,  # Almost entire series
        )
        assert len(analogs) <= 1
