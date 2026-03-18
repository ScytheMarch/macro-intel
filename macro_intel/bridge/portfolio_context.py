"""Connect regime model outputs to portfolio analytics.

Conditionally imports portfolio_lab for risk/factor/simulation analysis.
Falls back gracefully if portfolio_lab is not installed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from macro_intel.models.regime_hmm import RegimeResult
from macro_intel.models.asset_returns import (
    compute_regime_returns, current_regime_forecast, RegimeReturnProfile,
)

logger = logging.getLogger(__name__)

# Conditional portfolio_lab import
try:
    from portfolio_lab.analytics.risk import (
        covariance_matrix, portfolio_volatility, risk_contributions,
    )
    from portfolio_lab.analytics.performance import sharpe_ratio, sortino_ratio
    from portfolio_lab.analytics.factor_model import (
        run_factor_regression, portfolio_factor_exposures,
    )
    HAS_PORTFOLIO_LAB = True
except ImportError:
    HAS_PORTFOLIO_LAB = False
    logger.info("portfolio_lab not installed — portfolio bridge features limited")


@dataclass
class PortfolioBridgeResult:
    """Combined regime + portfolio analysis output."""
    # Current regime state
    current_regime: str
    regime_probability: float
    uncertainty: float

    # Regime-conditional return forecast
    expected_return: float | None
    expected_volatility: float | None
    regime_breakdown: list[dict] = field(default_factory=list)

    # Portfolio risk (if portfolio_lab available)
    portfolio_vol: float | None = None
    portfolio_sharpe: float | None = None
    risk_contrib: dict[str, float] | None = None
    factor_exposures: dict[str, float] | None = None

    # Warnings
    warnings: list[str] = field(default_factory=list)


def run_portfolio_bridge(
    regime_result: RegimeResult,
    holdings: dict[str, float] | None = None,
    price_data: pd.DataFrame | None = None,
    equity_returns: pd.Series | None = None,
    risk_free_rate: float = 0.04,
) -> PortfolioBridgeResult:
    """Run combined regime-portfolio analysis.

    Args:
        regime_result: Output from regime model
        holdings: Dict of ticker -> weight (for portfolio analysis)
        price_data: Daily prices DataFrame (tickers as columns) for risk calc
        equity_returns: Monthly equity index returns for regime conditioning
        risk_free_rate: Annual risk-free rate
    """
    warnings: list[str] = []

    # Current regime state
    current_probs = regime_result.regime_probs[-1]
    current_regime_idx = int(np.argmax(current_probs))
    current_regime = regime_result.regime_labels[current_regime_idx]
    regime_probability = float(current_probs[current_regime_idx])

    # Regime-conditional returns
    expected_return = None
    expected_vol = None
    breakdown: list[dict] = []

    if equity_returns is not None:
        profiles = compute_regime_returns(regime_result, equity_returns, risk_free_rate)
        forecast = current_regime_forecast(regime_result, profiles)
        expected_return = forecast.get("expected_return")
        expected_vol = forecast.get("expected_volatility")
        breakdown = forecast.get("breakdown", [])
    else:
        warnings.append("No equity returns provided — regime return forecast unavailable")

    # Portfolio analytics (requires portfolio_lab)
    portfolio_vol = None
    portfolio_sharpe = None
    risk_contrib = None
    factor_exps = None

    if holdings and price_data is not None and HAS_PORTFOLIO_LAB:
        try:
            tickers = list(holdings.keys())
            weights = np.array([holdings[t] for t in tickers])

            # Filter to available tickers
            available = [t for t in tickers if t in price_data.columns]
            if len(available) < len(tickers):
                missing = set(tickers) - set(available)
                warnings.append(f"Missing price data for: {missing}")

            if available:
                prices = price_data[available]
                returns = prices.pct_change().dropna()
                w = np.array([holdings[t] for t in available])
                w = w / w.sum()  # Renormalize

                cov = covariance_matrix(returns)
                portfolio_vol = float(portfolio_volatility(w, cov))
                portfolio_sharpe = float(sharpe_ratio(
                    w, returns.mean() * 252, cov, risk_free_rate,
                ))

                rc = risk_contributions(w, cov)
                risk_contrib = {t: round(float(rc[i]), 4) for i, t in enumerate(available)}

                # Factor exposures
                try:
                    factor_results = {
                        t: run_factor_regression(returns[t])
                        for t in available
                    }
                    factor_exps = dict(portfolio_factor_exposures(
                        {t: r for t, r in factor_results.items()},
                        {t: holdings[t] for t in available},
                    ))
                except Exception as e:
                    warnings.append(f"Factor analysis failed: {e}")

        except Exception as e:
            warnings.append(f"Portfolio analytics failed: {e}")
            logger.error("Portfolio bridge error: %s", e)

    elif holdings and not HAS_PORTFOLIO_LAB:
        warnings.append("Install portfolio_lab for full portfolio analytics")

    return PortfolioBridgeResult(
        current_regime=current_regime,
        regime_probability=regime_probability,
        uncertainty=regime_result.uncertainty,
        expected_return=expected_return,
        expected_volatility=expected_vol,
        regime_breakdown=breakdown,
        portfolio_vol=portfolio_vol,
        portfolio_sharpe=portfolio_sharpe,
        risk_contrib=risk_contrib,
        factor_exposures=factor_exps,
        warnings=warnings,
    )
