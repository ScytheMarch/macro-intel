"""Tests for regime model components (priors, forward-backward, labeling)."""

from __future__ import annotations

import numpy as np
import pytest

from macro_intel.models.priors import (
    RegimePriors,
    REGIME_PRIORS_DEFAULT,
    REGIME_PRIORS_CONSERVATIVE,
    REGIME_PRIORS_EXPLORATORY,
    REGIME_SIGNATURES,
)
from macro_intel.models.regime_hmm import (
    _forward_backward,
    _logsumexp,
    _logsumexp_2d,
    _label_regimes,
    _prepare_data,
    RegimeResult,
)


class TestRegimePriors:
    def test_default_priors(self):
        p = REGIME_PRIORS_DEFAULT
        assert p.n_regimes == 4
        assert p.stickiness_kappa == 10.0
        assert len(p.regime_labels) == 4

    def test_conservative_priors(self):
        p = REGIME_PRIORS_CONSERVATIVE
        assert p.stickiness_kappa > REGIME_PRIORS_DEFAULT.stickiness_kappa
        assert p.tau_sd < REGIME_PRIORS_DEFAULT.tau_sd

    def test_exploratory_priors(self):
        p = REGIME_PRIORS_EXPLORATORY
        assert p.stickiness_kappa < REGIME_PRIORS_DEFAULT.stickiness_kappa
        assert p.tau_sd > REGIME_PRIORS_DEFAULT.tau_sd

    def test_frozen_dataclass(self):
        with pytest.raises(AttributeError):
            REGIME_PRIORS_DEFAULT.n_regimes = 3  # type: ignore

    def test_regime_signatures_keys(self):
        assert set(REGIME_SIGNATURES.keys()) == {"Expansion", "Slowdown", "Stagflation", "Crisis"}


class TestLogsumexp:
    def test_simple(self):
        a = np.array([0.0, 0.0])
        result = _logsumexp(a)
        assert abs(result - np.log(2.0)) < 1e-10

    def test_large_values(self):
        """Numerically stable with large values."""
        a = np.array([1000.0, 1000.0])
        result = _logsumexp(a)
        assert abs(result - (1000 + np.log(2))) < 1e-6

    def test_negative_values(self):
        a = np.array([-100.0, -200.0])
        result = _logsumexp(a)
        assert np.isfinite(result)


class TestLogsumexp2D:
    def test_row_wise(self):
        a = np.array([[0.0, 0.0], [1.0, 2.0]])
        result = _logsumexp_2d(a)
        assert result.shape == (2, 1)
        assert abs(result[0, 0] - np.log(2.0)) < 1e-10


class TestForwardBackward:
    @pytest.fixture
    def hmm_params(self):
        """Simple 2-state HMM parameters."""
        K, F = 2, 3
        np.random.seed(42)
        T = 30

        mu = np.array([[1.0, 0.0, 0.5], [-1.0, 0.0, -0.5]])
        sigma = np.ones((K, F)) * 0.8
        P = np.array([[0.9, 0.1], [0.2, 0.8]])
        pi0 = np.array([0.6, 0.4])

        # Generate synthetic data from state 0
        X = np.random.randn(T, F) * 0.8 + mu[0]
        # Switch to state 1 halfway
        X[T // 2:] = np.random.randn(T - T // 2, F) * 0.8 + mu[1]

        return X, mu, sigma, P, pi0

    def test_output_shape(self, hmm_params):
        X, mu, sigma, P, pi0 = hmm_params
        probs = _forward_backward(X, mu, sigma, P, pi0)
        assert probs.shape == (len(X), 2)

    def test_probabilities_sum_to_one(self, hmm_params):
        X, mu, sigma, P, pi0 = hmm_params
        probs = _forward_backward(X, mu, sigma, P, pi0)
        row_sums = probs.sum(axis=1)
        np.testing.assert_allclose(row_sums, 1.0, atol=1e-6)

    def test_detects_state_switch(self, hmm_params):
        X, mu, sigma, P, pi0 = hmm_params
        probs = _forward_backward(X, mu, sigma, P, pi0)
        # First half should be mostly state 0
        assert probs[:10, 0].mean() > 0.5
        # Second half should be mostly state 1
        assert probs[-10:, 1].mean() > 0.5

    def test_probabilities_between_zero_and_one(self, hmm_params):
        X, mu, sigma, P, pi0 = hmm_params
        probs = _forward_backward(X, mu, sigma, P, pi0)
        assert np.all(probs >= 0)
        assert np.all(probs <= 1.0 + 1e-6)


class TestLabelRegimes:
    def test_returns_correct_count(self):
        K, F = 4, 6
        mu = np.random.randn(K, F)
        features = ["CPIAUCSL", "UNRATE", "GDPC1", "INDPRO", "FEDFUNDS", "VIXCLS"]
        labels = _label_regimes(mu, features)
        assert len(labels) == K

    def test_all_labels_assigned(self):
        K, F = 4, 6
        mu = np.random.randn(K, F)
        features = ["CPIAUCSL", "UNRATE", "GDPC1", "INDPRO", "FEDFUNDS", "VIXCLS"]
        labels = _label_regimes(mu, features)
        # All labels should be non-empty strings
        assert all(isinstance(l, str) and len(l) > 0 for l in labels)

    def test_handles_unknown_features(self):
        """Works even when features don't match signatures."""
        K, F = 4, 3
        mu = np.random.randn(K, F)
        features = ["FEAT_A", "FEAT_B", "FEAT_C"]
        labels = _label_regimes(mu, features)
        assert len(labels) == K


class TestPrepareData:
    def test_single_country(self, single_country_panel):
        X, features, countries, dates = _prepare_data(
            single_country_panel, ["USA"]
        )
        assert X.ndim == 2
        assert countries == ["USA"]
        assert len(dates) > 0

    def test_multi_country(self, sample_panel):
        X, features, countries, dates = _prepare_data(
            sample_panel, ["USA", "GBR"]
        )
        # Could be 2D (if insufficient common dates) or 3D
        assert X.ndim in (2, 3)
        assert len(countries) >= 1

    def test_no_valid_features_raises(self, sample_panel):
        with pytest.raises(ValueError, match="No valid feature"):
            _prepare_data(sample_panel, ["USA"], feature_cols=["NONEXISTENT"])


class TestRegimeResult:
    def test_dataclass_fields(self, sample_regime_result):
        r = sample_regime_result
        assert r.regime_probs.shape == (60, 4)
        assert len(r.regime_labels) == 4
        assert r.transition_matrix.shape == (4, 4)
        assert 0 <= r.uncertainty <= 1
        assert len(r.countries) == 1
        assert len(r.dates) == 60
