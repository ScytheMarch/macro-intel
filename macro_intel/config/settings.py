"""Global settings with lazy secret resolution for CLI and Streamlit compatibility."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_env_file = _PROJECT_ROOT / ".env"
if _env_file.exists():
    load_dotenv(_env_file, override=False)


def _get_secret(key: str, default: str = "") -> str:
    """Try Streamlit secrets first, then fall back to env var."""
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            val = st.secrets.get(key)
            if val:
                return str(val)
    except Exception:
        pass
    return os.getenv(key, default)


class Settings:
    """Macro-Intel configuration — lazy-loaded, environment-aware."""

    @property
    def fred_api_key(self) -> str:
        return _get_secret("FRED_API_KEY")

    @property
    def project_root(self) -> Path:
        return _PROJECT_ROOT

    @property
    def db_path(self) -> Path:
        custom = os.getenv("MACRO_INTEL_DB_PATH")
        if custom:
            return Path(custom)
        return _PROJECT_ROOT / "data" / "macro_intel.db"

    @property
    def model_dir(self) -> Path:
        custom = os.getenv("MACRO_INTEL_MODEL_DIR")
        p = Path(custom) if custom else _PROJECT_ROOT / "data" / "models"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def reports_dir(self) -> Path:
        custom = os.getenv("MACRO_INTEL_REPORTS_DIR")
        p = Path(custom) if custom else _PROJECT_ROOT / "data" / "reports"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def default_lookback_years(self) -> int:
        return int(os.getenv("MACRO_INTEL_LOOKBACK_YEARS", "10"))

    # PyMC sampling defaults
    @property
    def pymc_draws(self) -> int:
        return int(os.getenv("PYMC_DRAWS", "2000"))

    @property
    def pymc_tune(self) -> int:
        return int(os.getenv("PYMC_TUNE", "1000"))

    @property
    def pymc_chains(self) -> int:
        return int(os.getenv("PYMC_CHAINS", "4"))

    @property
    def n_regimes(self) -> int:
        return int(os.getenv("MACRO_INTEL_N_REGIMES", "4"))


settings = Settings()
