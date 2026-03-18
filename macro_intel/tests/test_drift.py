"""Tests for monitoring / drift detection components."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from macro_intel.monitoring.drift import DriftConfig, DriftResult
from macro_intel.monitoring.data_quality import QualityResult


class TestDriftConfig:
    def test_defaults(self):
        cfg = DriftConfig()
        assert cfg.reference_months == 12
        assert cfg.current_months == 3
        assert cfg.country == "USA"


class TestDriftResult:
    def test_construction(self):
        r = DriftResult(
            dataset_drift=True,
            n_drifted_features=3,
            n_total_features=10,
            drift_share=0.3,
            feature_details={"CPI": {"drifted": True, "drift_score": 0.8}},
        )
        assert r.dataset_drift is True
        assert r.drift_share == 0.3
        assert r.report_path is None


class TestQualityResult:
    def test_construction(self):
        r = QualityResult(
            n_rows=100,
            n_columns=10,
            missing_pct=5.0,
            columns_with_issues=["CPI"],
            summary={"CPI": {"missing_pct": 5.0}},
        )
        assert r.n_rows == 100
        assert len(r.columns_with_issues) == 1
        assert "CPI" in r.summary
