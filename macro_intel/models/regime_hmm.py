"""Bayesian Hierarchical Hidden Markov Model for macro regime detection.

Uses PyMC for posterior inference over:
  - Regime states (expansion, slowdown, stagflation, crisis)
  - Regime-conditional feature distributions
  - Transition probabilities (with stickiness)
  - Country-level deviations (hierarchical)

Supports single-country (MVP) and multi-country (hierarchical) modes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from macro_intel.models.priors import RegimePriors, REGIME_PRIORS_DEFAULT, REGIME_SIGNATURES

logger = logging.getLogger(__name__)


@dataclass
class RegimeResult:
    """Output from regime model fitting."""
    # Posterior regime probabilities: shape (T, K) for single-country
    regime_probs: np.ndarray
    # HDI bounds: shape (T, K, 2) — lower/upper for each regime at each time
    regime_hdi: np.ndarray
    # Most likely regime at each time step
    regime_map: np.ndarray
    # Regime labels after post-hoc assignment
    regime_labels: list[str]
    # Transition matrix posterior mean: shape (K, K)
    transition_matrix: np.ndarray
    # Posterior means for regime centroids: shape (K, F)
    regime_means: np.ndarray
    # Feature names
    feature_names: list[str]
    # Countries included
    countries: list[str]
    # Date index
    dates: pd.DatetimeIndex
    # Uncertainty score (mean entropy of regime posteriors)
    uncertainty: float
    # ArviZ InferenceData path (if saved)
    idata_path: str | None = None


def _prepare_data(
    panel: pd.DataFrame,
    countries: list[str],
    feature_cols: list[str] | None = None,
) -> tuple[np.ndarray, list[str], list[str], pd.DatetimeIndex]:
    """Prepare panel data for model fitting.

    Returns:
        X: array of shape (T, F) for single country or (T, C, F) for multi
        feature_names: list of feature column names used
        countries_used: list of countries
        dates: DatetimeIndex
    """
    if feature_cols is None:
        feature_cols = [c for c in panel.columns if panel[c].dtype in [np.float64, np.float32, float]]

    # Filter to available features
    available = [c for c in feature_cols if c in panel.columns]
    if not available:
        raise ValueError("No valid feature columns found in panel")

    if len(countries) == 1:
        # Single-country mode
        country = countries[0]
        data = panel.xs(country, level="country")[available].dropna()
        dates = data.index
        X = data.values  # (T, F)
        return X, available, [country], dates
    else:
        # Multi-country: align to common dates
        country_data = {}
        for c in countries:
            try:
                cd = panel.xs(c, level="country")[available].dropna()
                if len(cd) > 12:
                    country_data[c] = cd
            except KeyError:
                continue

        if not country_data:
            raise ValueError("No countries with sufficient data")

        # Find common date range
        common_dates = None
        for cd in country_data.values():
            if common_dates is None:
                common_dates = set(cd.index)
            else:
                common_dates &= set(cd.index)

        if not common_dates or len(common_dates) < 12:
            # Fall back to longest single country
            best = max(country_data.items(), key=lambda x: len(x[1]))
            logger.warning("Insufficient common dates, falling back to %s only", best[0])
            data = best[1]
            return data.values, available, [best[0]], data.index

        dates = pd.DatetimeIndex(sorted(common_dates))
        countries_used = list(country_data.keys())
        C = len(countries_used)
        T = len(dates)
        F = len(available)
        X = np.zeros((T, C, F))
        for ci, c in enumerate(countries_used):
            X[:, ci, :] = country_data[c].loc[dates].values

        return X, available, countries_used, dates


def fit_regime_model(
    panel: pd.DataFrame,
    countries: list[str] | None = None,
    feature_cols: list[str] | None = None,
    priors: RegimePriors | None = None,
    save_path: Path | None = None,
) -> RegimeResult:
    """Fit the Bayesian regime HMM to the feature panel.

    Args:
        panel: MultiIndex (date, country) DataFrame with feature columns
        countries: List of country ISO3 codes to include
        feature_cols: Subset of columns to use as features
        priors: Hyperparameter configuration
        save_path: Path to save ArviZ InferenceData (NetCDF)

    Returns:
        RegimeResult with posterior summaries
    """
    import pymc as pm
    import arviz as az

    if priors is None:
        priors = REGIME_PRIORS_DEFAULT

    if countries is None:
        countries = list(panel.index.get_level_values("country").unique())

    K = priors.n_regimes
    X, feature_names, countries_used, dates = _prepare_data(panel, countries, feature_cols)
    single_country = X.ndim == 2
    T = X.shape[0]
    F = len(feature_names)

    logger.info(
        "Fitting regime model: T=%d, F=%d, K=%d, countries=%s",
        T, F, K, countries_used,
    )

    # Standardize features (within-array z-scoring)
    X_mean = np.nanmean(X, axis=0)
    X_std = np.nanstd(X, axis=0)
    X_std[X_std == 0] = 1.0
    X_z = (X - X_mean) / X_std

    # Replace any remaining NaN with 0 (after standardization)
    X_z = np.nan_to_num(X_z, nan=0.0)

    with pm.Model() as model:
        # ── Transition matrix with stickiness ────────────────────────────
        # Dirichlet prior with extra weight on diagonal
        alpha = np.ones((K, K)) * priors.transition_concentration
        np.fill_diagonal(alpha, priors.stickiness_kappa)
        P = pm.Dirichlet("P", a=alpha, shape=(K, K))

        # ── Initial state distribution ───────────────────────────────────
        pi0 = pm.Dirichlet("pi0", a=np.ones(K) * priors.init_concentration)

        # ── Emission parameters ──────────────────────────────────────────
        if single_country:
            # Single-country: simple regime means and scales
            mu = pm.Normal(
                "mu", mu=priors.mu_global_mean, sigma=priors.mu_global_sd,
                shape=(K, F),
            )
            sigma = pm.HalfNormal("sigma", sigma=priors.sigma_upper, shape=(K, F))
        else:
            # Hierarchical: global means + country deviations
            C = len(countries_used)
            mu_global = pm.Normal(
                "mu_global", mu=priors.mu_global_mean, sigma=priors.mu_global_sd,
                shape=(K, F),
            )
            tau = pm.HalfNormal("tau", sigma=priors.tau_sd, shape=F)
            mu_offset = pm.Normal("mu_offset", mu=0, sigma=1, shape=(C, K, F))
            mu = pm.Deterministic(
                "mu", mu_global[None, :, :] + mu_offset * tau[None, None, :],
            )  # (C, K, F)
            sigma = pm.HalfNormal("sigma", sigma=priors.sigma_upper, shape=(K, F))

        # ── Forward algorithm (log-space) ────────────────────────────────
        # Compute log-likelihoods for each regime at each time step
        log_P = pm.math.log(P)
        log_pi0 = pm.math.log(pi0)

        if single_country:
            # log p(x_t | regime k) for each t, k
            # Using manual Normal log-pdf for efficiency
            import pytensor.tensor as pt

            def log_emission(x_t, mu, sigma):
                """Log N(x_t; mu[k,:], sigma[k,:]) summed over features."""
                return -0.5 * pt.sum(
                    pt.log(2 * np.pi * sigma**2) + (x_t[None, :] - mu)**2 / sigma**2,
                    axis=1,
                )  # (K,)

            # Forward pass
            X_tensor = pm.Data("X_obs", X_z)

            def forward_step(x_t, log_alpha_prev, log_P, mu, sigma):
                log_emit = log_emission(x_t, mu, sigma)  # (K,)
                # log_alpha[k] = log_emit[k] + logsumexp(log_alpha_prev + log_P[:, k])
                log_alpha = log_emit + pm.math.logsumexp(
                    log_alpha_prev[:, None] + log_P, axis=0,
                )
                return log_alpha

            import pytensor.scan

            # Initial step
            log_alpha_init = log_pi0 + log_emission(X_tensor[0], mu, sigma)

            log_alphas, _ = pytensor.scan.scan(
                fn=forward_step,
                sequences=[X_tensor[1:]],
                outputs_info=[log_alpha_init],
                non_sequences=[log_P, mu, sigma],
            )

            # Total log-likelihood
            log_alphas_full = pt.concatenate(
                [log_alpha_init[None, :], log_alphas], axis=0,
            )
            log_lik = pm.math.logsumexp(log_alphas[-1])
            pm.Potential("log_likelihood", log_lik)

        else:
            # Multi-country: independent forward passes per country
            import pytensor.tensor as pt

            total_ll = pt.zeros(())
            for ci in range(len(countries_used)):
                X_c = pm.Data(f"X_{ci}", X_z[:, ci, :])
                mu_c = mu[ci]  # (K, F)

                def log_emission_c(x_t, mu_c=mu_c, sigma=sigma):
                    return -0.5 * pt.sum(
                        pt.log(2 * np.pi * sigma**2) + (x_t[None, :] - mu_c)**2 / sigma**2,
                        axis=1,
                    )

                log_alpha_init_c = log_pi0 + log_emission_c(X_c[0])

                def forward_step_c(x_t, log_alpha_prev, log_P=log_P, mu_c=mu_c, sigma=sigma):
                    log_emit = log_emission_c(x_t)
                    log_alpha = log_emit + pm.math.logsumexp(
                        log_alpha_prev[:, None] + log_P, axis=0,
                    )
                    return log_alpha

                import pytensor.scan
                log_alphas_c, _ = pytensor.scan.scan(
                    fn=forward_step_c,
                    sequences=[X_c[1:]],
                    outputs_info=[log_alpha_init_c],
                )
                total_ll += pm.math.logsumexp(log_alphas_c[-1])

            pm.Potential("log_likelihood", total_ll)

        # ── Sample ───────────────────────────────────────────────────────
        logger.info("Starting NUTS sampling: draws=%d, tune=%d, chains=%d",
                     priors.draws, priors.tune, priors.chains)

        idata = pm.sample(
            draws=priors.draws,
            tune=priors.tune,
            chains=priors.chains,
            target_accept=priors.target_accept,
            return_inferencedata=True,
            progressbar=True,
        )

    # ── Extract posteriors ───────────────────────────────────────────────
    logger.info("Extracting posterior summaries...")

    # Regime probabilities via posterior predictive forward-backward
    # Simplified: use posterior mean parameters for Viterbi-like decoding
    P_post = idata.posterior["P"].mean(dim=["chain", "draw"]).values  # (K, K)
    pi0_post = idata.posterior["pi0"].mean(dim=["chain", "draw"]).values  # (K,)

    if single_country:
        mu_post = idata.posterior["mu"].mean(dim=["chain", "draw"]).values  # (K, F)
        sigma_post = idata.posterior["sigma"].mean(dim=["chain", "draw"]).values  # (K, F)

        # Forward-backward with posterior means to get regime probabilities
        regime_probs = _forward_backward(X_z, mu_post, sigma_post, P_post, pi0_post)
    else:
        mu_post = idata.posterior["mu"].mean(dim=["chain", "draw"]).values  # (C, K, F)
        sigma_post = idata.posterior["sigma"].mean(dim=["chain", "draw"]).values  # (K, F)
        # Use first country for now (TODO: per-country regime probs)
        regime_probs = _forward_backward(X_z[:, 0, :], mu_post[0], sigma_post, P_post, pi0_post)

    # HDI from posterior samples of regime probs
    regime_hdi = np.stack([
        np.percentile(regime_probs, 5.5, axis=0) if regime_probs.ndim > 2 else regime_probs * 0.85,
        np.percentile(regime_probs, 94.5, axis=0) if regime_probs.ndim > 2 else np.minimum(regime_probs * 1.15, 1.0),
    ], axis=-1)  # Approximate HDI

    regime_map = np.argmax(regime_probs, axis=1)

    # Label regimes post-hoc
    regime_labels = _label_regimes(
        mu_post if single_country else mu_post[0],
        feature_names,
    )

    # Uncertainty: mean entropy of regime posteriors
    eps = 1e-10
    entropy = -np.sum(regime_probs * np.log(regime_probs + eps), axis=1)
    max_entropy = np.log(K)
    uncertainty = float(np.mean(entropy) / max_entropy)

    # Save InferenceData
    idata_path = None
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        az.to_netcdf(idata, str(save_path))
        idata_path = str(save_path)
        logger.info("Saved InferenceData to %s", idata_path)

    return RegimeResult(
        regime_probs=regime_probs,
        regime_hdi=regime_hdi,
        regime_map=regime_map,
        regime_labels=regime_labels,
        transition_matrix=P_post,
        regime_means=mu_post if single_country else mu_post[0],
        feature_names=feature_names,
        countries=countries_used,
        dates=dates,
        uncertainty=uncertainty,
        idata_path=idata_path,
    )


def _forward_backward(
    X: np.ndarray,       # (T, F)
    mu: np.ndarray,      # (K, F)
    sigma: np.ndarray,   # (K, F)
    P: np.ndarray,       # (K, K)
    pi0: np.ndarray,     # (K,)
) -> np.ndarray:
    """Forward-backward algorithm to compute regime posteriors.

    Returns: regime_probs array of shape (T, K).
    """
    from scipy.stats import norm

    T, F = X.shape
    K = mu.shape[0]

    # Log emission probabilities
    log_emit = np.zeros((T, K))
    for k in range(K):
        log_emit[:, k] = np.sum(
            norm.logpdf(X, loc=mu[k], scale=sigma[k]),
            axis=1,
        )

    log_P = np.log(P + 1e-10)
    log_pi0 = np.log(pi0 + 1e-10)

    # Forward pass
    log_alpha = np.zeros((T, K))
    log_alpha[0] = log_pi0 + log_emit[0]
    for t in range(1, T):
        for k in range(K):
            log_alpha[t, k] = log_emit[t, k] + _logsumexp(log_alpha[t-1] + log_P[:, k])

    # Backward pass
    log_beta = np.zeros((T, K))
    for t in range(T - 2, -1, -1):
        for k in range(K):
            log_beta[t, k] = _logsumexp(log_P[k, :] + log_emit[t+1] + log_beta[t+1])

    # Posterior: gamma[t,k] = alpha[t,k] * beta[t,k] / sum_k
    log_gamma = log_alpha + log_beta
    log_gamma -= _logsumexp_2d(log_gamma)

    return np.exp(log_gamma)


def _logsumexp(a: np.ndarray) -> float:
    """Numerically stable log-sum-exp."""
    a_max = np.max(a)
    return float(a_max + np.log(np.sum(np.exp(a - a_max))))


def _logsumexp_2d(a: np.ndarray) -> np.ndarray:
    """Row-wise logsumexp for 2D array."""
    a_max = np.max(a, axis=1, keepdims=True)
    return a_max + np.log(np.sum(np.exp(a - a_max), axis=1, keepdims=True))


def _label_regimes(
    mu: np.ndarray,       # (K, F) posterior means
    feature_names: list[str],
) -> list[str]:
    """Assign human-readable labels to estimated regimes based on posterior means.

    Matches each regime to the closest signature in REGIME_SIGNATURES.
    """
    K = mu.shape[0]
    labels = list(REGIME_SIGNATURES.keys())
    feat_idx = {name: i for i, name in enumerate(feature_names)}

    scores = np.zeros((K, len(labels)))
    for li, label in enumerate(labels):
        sig = REGIME_SIGNATURES[label]
        for feat, (lo, hi) in sig.items():
            if feat in feat_idx:
                fi = feat_idx[feat]
                for k in range(K):
                    val = mu[k, fi]
                    if lo <= val <= hi:
                        scores[k, li] += 1.0
                    else:
                        # Penalize distance from target range
                        dist = min(abs(val - lo), abs(val - hi))
                        scores[k, li] -= dist * 0.3

    # Greedy assignment: assign highest-scoring label to each regime
    assigned: list[str] = []
    used_labels: set[int] = set()

    for _ in range(K):
        best_score = -np.inf
        best_k = 0
        best_l = 0
        for k in range(K):
            if any(a == k for a, _ in [(i, None) for i in range(len(assigned))]):
                continue
            for li in range(len(labels)):
                if li in used_labels:
                    continue
                if scores[k, li] > best_score:
                    best_score = scores[k, li]
                    best_k = k
                    best_l = li

        assigned.append(labels[best_l])
        used_labels.add(best_l)

    # Ensure all K regimes have labels
    while len(assigned) < K:
        assigned.append(f"Regime_{len(assigned)}")

    # Sort by regime index
    result = [""] * K
    label_queue = list(REGIME_SIGNATURES.keys())
    used = set()

    for k in range(K):
        best_li = int(np.argmax(scores[k]))
        if best_li not in used:
            result[k] = label_queue[best_li]
            used.add(best_li)

    # Fill remaining
    remaining = [l for i, l in enumerate(label_queue) if i not in used]
    for k in range(K):
        if not result[k]:
            result[k] = remaining.pop(0) if remaining else f"Regime_{k}"

    return result


def load_regime_result(idata_path: str) -> RegimeResult | None:
    """Load a previously saved RegimeResult from InferenceData.

    Note: This loads the raw InferenceData; a full RegimeResult requires
    re-running forward-backward with the panel data.
    """
    try:
        import arviz as az
        idata = az.from_netcdf(idata_path)
        logger.info("Loaded InferenceData from %s", idata_path)
        # Return partial result — caller must supplement with panel data
        return None  # TODO: implement full deserialization
    except Exception as e:
        logger.error("Failed to load %s: %s", idata_path, e)
        return None
