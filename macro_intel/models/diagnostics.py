"""MCMC diagnostics and convergence checks using ArviZ."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def check_convergence(idata_path: str | Path) -> dict:
    """Run convergence diagnostics on saved InferenceData.

    Returns dict with:
        - rhat_max: maximum R-hat across all parameters
        - ess_min: minimum effective sample size
        - divergences: number of divergent transitions
        - converged: bool (True if all checks pass)
        - details: per-variable summaries
    """
    import arviz as az

    idata = az.from_netcdf(str(idata_path))
    summary = az.summary(idata, round_to=4)

    rhat_max = float(summary["r_hat"].max()) if "r_hat" in summary.columns else 1.0
    ess_min = float(summary["ess_bulk"].min()) if "ess_bulk" in summary.columns else 0.0

    # Count divergences
    divergences = 0
    if hasattr(idata, "sample_stats") and "diverging" in idata.sample_stats:
        divergences = int(idata.sample_stats["diverging"].sum().values)

    converged = (rhat_max < 1.05) and (ess_min > 400) and (divergences == 0)

    return {
        "rhat_max": rhat_max,
        "ess_min": ess_min,
        "divergences": divergences,
        "converged": converged,
        "n_params": len(summary),
        "details": summary.to_dict() if len(summary) < 200 else "Too many params for inline display",
    }


def posterior_summary(idata_path: str | Path, var_names: list[str] | None = None) -> dict:
    """Get posterior summary statistics for specified variables."""
    import arviz as az

    idata = az.from_netcdf(str(idata_path))
    summary = az.summary(idata, var_names=var_names, round_to=4, hdi_prob=0.89)
    return summary.to_dict()


def compute_waic(idata_path: str | Path) -> dict:
    """Compute WAIC for model comparison."""
    import arviz as az

    try:
        idata = az.from_netcdf(str(idata_path))
        waic = az.waic(idata)
        return {
            "waic": float(waic.elpd_waic) * -2,
            "p_waic": float(waic.p_waic),
            "se": float(waic.se),
        }
    except Exception as e:
        logger.warning("WAIC computation failed: %s", e)
        return {"waic": None, "p_waic": None, "se": None}
