"""SQLite storage layer with country dimension for multi-country macro data.

Tables:
  - observations: time series data (series_id, country, date, value)
  - series_metadata: last_updated, last_fetched, title, etc.
  - model_runs: log of model fitting runs
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import pandas as pd

from macro_intel.config.settings import settings


def _db_path() -> Path:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    return settings.db_path


@contextmanager
def _connect() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(_db_path()), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they don't exist."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS observations (
                series_id TEXT NOT NULL,
                country   TEXT NOT NULL DEFAULT 'USA',
                date      TEXT NOT NULL,
                value     REAL,
                PRIMARY KEY (series_id, country, date)
            );

            CREATE TABLE IF NOT EXISTS series_metadata (
                series_id    TEXT NOT NULL,
                country      TEXT NOT NULL DEFAULT 'USA',
                source       TEXT NOT NULL DEFAULT 'fred',
                title        TEXT,
                frequency    TEXT,
                units        TEXT,
                last_updated TEXT,
                last_fetched TEXT,
                PRIMARY KEY (series_id, country)
            );

            CREATE TABLE IF NOT EXISTS model_runs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp  TEXT NOT NULL,
                model_type TEXT NOT NULL,
                countries  TEXT,
                n_features INTEGER,
                n_regimes  INTEGER,
                draws      INTEGER,
                artifact   TEXT,
                notes      TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_obs_series
                ON observations(series_id, country);
            CREATE INDEX IF NOT EXISTS idx_obs_date
                ON observations(date);
        """)


# ── Observations ─────────────────────────────────────────────────────────────

def upsert_observations(
    series_id: str,
    df: pd.DataFrame,
    country: str = "USA",
) -> int:
    """Write observations. df must have DatetimeIndex and 'value' column."""
    if df.empty:
        return 0

    rows = [
        (series_id, country, idx.strftime("%Y-%m-%d"), float(row["value"]))
        for idx, row in df.iterrows()
        if pd.notna(row["value"])
    ]
    with _connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO observations (series_id, country, date, value) "
            "VALUES (?, ?, ?, ?)",
            rows,
        )
    return len(rows)


def get_observations(
    series_id: str,
    country: str = "USA",
    start_date: str | None = None,
) -> pd.DataFrame:
    """Read observations for a series + country. Returns df with DatetimeIndex."""
    query = "SELECT date, value FROM observations WHERE series_id = ? AND country = ?"
    params: list = [series_id, country]
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    query += " ORDER BY date"

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()

    if not rows:
        return pd.DataFrame(columns=["value"])

    df = pd.DataFrame(rows, columns=["date", "value"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    return df


def get_all_series_for_country(country: str = "USA") -> dict[str, pd.DataFrame]:
    """Return all cached series for a given country."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT series_id FROM observations WHERE country = ?",
            (country,),
        ).fetchall()

    result = {}
    for row in rows:
        sid = row["series_id"]
        result[sid] = get_observations(sid, country)
    return result


def get_latest(series_id: str, country: str = "USA") -> tuple[str | None, float | None]:
    """Return (date_str, value) for the most recent observation."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT date, value FROM observations "
            "WHERE series_id = ? AND country = ? ORDER BY date DESC LIMIT 1",
            (series_id, country),
        ).fetchone()
    if row:
        return row["date"], row["value"]
    return None, None


# ── Metadata ─────────────────────────────────────────────────────────────────

def upsert_metadata(
    series_id: str,
    country: str = "USA",
    source: str = "fred",
    title: str = "",
    frequency: str = "",
    units: str = "",
    last_updated: str = "",
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """INSERT INTO series_metadata
               (series_id, country, source, title, frequency, units, last_updated, last_fetched)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(series_id, country) DO UPDATE SET
                   title = COALESCE(NULLIF(excluded.title, ''), series_metadata.title),
                   frequency = COALESCE(NULLIF(excluded.frequency, ''), series_metadata.frequency),
                   units = COALESCE(NULLIF(excluded.units, ''), series_metadata.units),
                   last_updated = COALESCE(NULLIF(excluded.last_updated, ''), series_metadata.last_updated),
                   last_fetched = excluded.last_fetched
            """,
            (series_id, country, source, title, frequency, units, last_updated, now),
        )


def get_metadata(series_id: str, country: str = "USA") -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM series_metadata WHERE series_id = ? AND country = ?",
            (series_id, country),
        ).fetchone()
    return dict(row) if row else None


def is_stale(series_id: str, country: str = "USA", max_age_hours: int = 24) -> bool:
    meta = get_metadata(series_id, country)
    if not meta or not meta.get("last_fetched"):
        return True
    last = datetime.fromisoformat(meta["last_fetched"])
    age = datetime.now(timezone.utc) - last
    return age.total_seconds() > max_age_hours * 3600


# ── Model Runs ───────────────────────────────────────────────────────────────

def log_model_run(
    model_type: str,
    countries: list[str],
    n_features: int,
    n_regimes: int,
    draws: int,
    artifact: str,
    notes: str = "",
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cursor = conn.execute(
            """INSERT INTO model_runs
               (timestamp, model_type, countries, n_features, n_regimes, draws, artifact, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (now, model_type, ",".join(countries), n_features, n_regimes, draws, artifact, notes),
        )
        return cursor.lastrowid or 0


def get_latest_model_run(model_type: str = "regime_hmm") -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM model_runs WHERE model_type = ? ORDER BY timestamp DESC LIMIT 1",
            (model_type,),
        ).fetchone()
    return dict(row) if row else None


# Initialize on import
init_db()
