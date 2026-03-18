"""Prior specifications for the Bayesian regime model.

Encapsulates all hyperparameter choices for the hierarchical HMM.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RegimePriors:
    """Hyperparameters for the regime HMM."""

    # Number of regimes
    n_regimes: int = 4

    # Regime labels (assigned post-hoc by examining posterior means)
    regime_labels: tuple[str, ...] = (
        "Expansion", "Slowdown", "Stagflation", "Crisis",
    )

    # Emission priors: regime-specific feature means
    mu_global_mean: float = 0.0     # Prior mean for global regime centroids
    mu_global_sd: float = 2.0       # Prior sd — wide to let data speak

    # Emission priors: regime-specific feature scales
    sigma_lower: float = 0.1        # HalfNormal lower bound for emission sd
    sigma_upper: float = 3.0        # HalfNormal sd parameter

    # Hierarchical pooling: how much countries can deviate from global
    tau_sd: float = 0.5             # Tighter = more pooling toward global

    # Transition matrix priors
    transition_concentration: float = 1.0   # Dirichlet concentration (base)
    stickiness_kappa: float = 10.0          # Extra weight on diagonal (staying in same regime)

    # Initial state prior (uniform)
    init_concentration: float = 1.0

    # Sampling config
    draws: int = 2000
    tune: int = 1000
    chains: int = 4
    target_accept: float = 0.9

    # Feature selection for model input
    # These are the z-scored features the model sees
    # (populated at runtime from panel columns)
    feature_names: tuple[str, ...] = ()


# Default prior configs for different scenarios
REGIME_PRIORS_DEFAULT = RegimePriors()

REGIME_PRIORS_CONSERVATIVE = RegimePriors(
    mu_global_sd=1.5,
    tau_sd=0.3,          # Stronger pooling
    stickiness_kappa=15.0,  # Regimes last longer
    draws=3000,
    tune=1500,
)

REGIME_PRIORS_EXPLORATORY = RegimePriors(
    mu_global_sd=3.0,
    tau_sd=1.0,          # Weaker pooling, more country variation
    stickiness_kappa=5.0,   # More regime switching
    draws=1500,
    tune=800,
)


# Post-hoc regime labeling criteria (z-score ranges for key features)
# Used to match estimated regimes to economic labels
REGIME_SIGNATURES: dict[str, dict[str, tuple[float, float]]] = {
    "Expansion": {
        "GDPC1": (0.0, 3.0),       # Positive GDP growth
        "UNRATE": (-3.0, -0.5),     # Below-average unemployment
        "INDPRO": (0.0, 3.0),       # Rising industrial production
        "VIXCLS": (-2.0, 0.0),      # Low volatility
    },
    "Slowdown": {
        "GDPC1": (-1.0, 0.5),       # Slowing growth
        "UNRATE": (-0.5, 1.0),      # Rising unemployment
        "UMCSENT": (-1.5, 0.0),     # Falling sentiment
    },
    "Stagflation": {
        "CPIAUCSL": (0.5, 3.0),     # High inflation
        "GDPC1": (-1.5, 0.0),       # Weak growth
        "UNRATE": (0.0, 2.0),       # Elevated unemployment
        "FEDFUNDS": (0.5, 3.0),     # Tight monetary policy
    },
    "Crisis": {
        "GDPC1": (-3.0, -1.0),      # Negative GDP
        "VIXCLS": (1.5, 5.0),       # Spiking volatility
        "BAMLH0A0HYM2": (1.5, 5.0), # Wide credit spreads
        "UNRATE": (1.0, 5.0),       # High unemployment
    },
}
