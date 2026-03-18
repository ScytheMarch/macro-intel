"""FRED data client via OpenBB SDK with direct API fallback.

Adapted from econ-monitor's openbb_client.py.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pandas as pd
import requests

from macro_intel.config.settings import settings

logger = logging.getLogger(__name__)

# ── OpenBB lazy init ─────────────────────────────────────────────────────────
_obb = None


def _get_obb():
    """Lazy-initialize OpenBB with FRED credentials."""
    global _obb
    if _obb is not None:
        return _obb
    try:
        from openbb import obb
        obb.user.credentials.fred_api_key = settings.fred_api_key
        _obb = obb
        logger.info("OpenBB SDK initialized with FRED credentials")
        return _obb
    except Exception as e:
        logger.warning("OpenBB unavailable (%s), using direct FRED API", e)
        return None


# ── Direct FRED API fallback ─────────────────────────────────────────────────
_FRED_BASE = "https://api.stlouisfed.org/fred"


def _fred_api_get(endpoint: str, params: dict) -> dict:
    params["api_key"] = settings.fred_api_key
    params["file_type"] = "json"
    resp = requests.get(f"{_FRED_BASE}/{endpoint}", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _fetch_via_fred_api(series_id: str, start_date: str | None = None) -> pd.DataFrame:
    params: dict = {"series_id": series_id}
    if start_date:
        params["observation_start"] = start_date

    data = _fred_api_get("series/observations", params)
    obs = data.get("observations", [])
    if not obs:
        return pd.DataFrame(columns=["value"])

    df = pd.DataFrame(obs)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df[["date", "value"]].dropna(subset=["value"])
    df = df.set_index("date")
    return df


# ── Public API ───────────────────────────────────────────────────────────────

def fetch_series(
    series_id: str,
    start_date: str | None = None,
    lookback_years: int | None = None,
) -> pd.DataFrame:
    """Fetch a FRED series. Returns DataFrame with DatetimeIndex and 'value' column."""
    if start_date is None and lookback_years:
        start_date = (datetime.now() - timedelta(days=lookback_years * 365)).strftime("%Y-%m-%d")

    obb = _get_obb()
    if obb is not None:
        try:
            result = obb.economy.fred_series(
                symbol=series_id,
                provider="fred",
                start_date=start_date,
            )
            df = result.to_df()
            if "value" not in df.columns:
                for col in ["close", series_id.lower(), "y"]:
                    if col in df.columns:
                        df = df.rename(columns={col: "value"})
                        break
                else:
                    numeric_cols = df.select_dtypes(include="number").columns
                    if len(numeric_cols) > 0:
                        df = df.rename(columns={numeric_cols[0]: "value"})
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date")
            df = df[["value"]].dropna()
            return df
        except Exception as e:
            logger.warning("OpenBB failed for %s (%s), trying direct API", series_id, e)

    return _fetch_via_fred_api(series_id, start_date)


def fetch_multiple(
    series_ids: list[str],
    start_date: str | None = None,
    lookback_years: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Fetch multiple FRED series. Returns dict of series_id -> DataFrame."""
    results = {}
    for sid in series_ids:
        try:
            results[sid] = fetch_series(sid, start_date, lookback_years)
        except Exception as e:
            logger.error("Failed to fetch %s: %s", sid, e)
            results[sid] = pd.DataFrame(columns=["value"])
    return results


def get_series_info(series_id: str) -> dict:
    """Get metadata for a FRED series."""
    try:
        data = _fred_api_get("series", {"series_id": series_id})
        seriess = data.get("seriess", [])
        if seriess:
            s = seriess[0]
            return {
                "title": s.get("title", ""),
                "frequency": s.get("frequency_short", ""),
                "units": s.get("units", ""),
                "last_updated": s.get("last_updated", ""),
            }
    except Exception as e:
        logger.error("Failed to get info for %s: %s", series_id, e)
    return {}
