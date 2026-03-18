"""Report generation and management for monitoring outputs."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from macro_intel.config.settings import settings
from macro_intel.monitoring.drift import DriftResult
from macro_intel.monitoring.data_quality import QualityResult

logger = logging.getLogger(__name__)


def save_monitoring_summary(
    drift_result: DriftResult | None = None,
    quality_result: QualityResult | None = None,
    country: str = "USA",
    output_dir: Path | None = None,
) -> str:
    """Save a JSON summary of all monitoring results.

    Returns path to the JSON file.
    """
    if output_dir is None:
        output_dir = settings.reports_dir

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"monitoring_{country}_{timestamp}.json"

    summary: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "country": country,
    }

    if drift_result:
        summary["drift"] = {
            "dataset_drift_detected": drift_result.dataset_drift,
            "drifted_features": drift_result.n_drifted_features,
            "total_features": drift_result.n_total_features,
            "drift_share": drift_result.drift_share,
            "report_path": drift_result.report_path,
            "top_drifted": sorted(
                [
                    {"feature": k, **v}
                    for k, v in drift_result.feature_details.items()
                    if v.get("drifted")
                ],
                key=lambda x: x.get("drift_score", 0),
                reverse=True,
            )[:10],
        }

    if quality_result:
        summary["quality"] = {
            "n_rows": quality_result.n_rows,
            "n_columns": quality_result.n_columns,
            "missing_pct": quality_result.missing_pct,
            "columns_with_issues": quality_result.columns_with_issues,
            "report_path": quality_result.report_path,
        }

    output_path.write_text(json.dumps(summary, indent=2, default=str))
    logger.info("Monitoring summary saved to %s", output_path)
    return str(output_path)


def get_latest_monitoring_report(
    country: str = "USA",
    report_dir: Path | None = None,
) -> dict | None:
    """Load the most recent monitoring summary for a country."""
    if report_dir is None:
        report_dir = settings.reports_dir

    if not report_dir.exists():
        return None

    pattern = f"monitoring_{country}_*.json"
    files = sorted(report_dir.glob(pattern), reverse=True)
    if not files:
        return None

    try:
        return json.loads(files[0].read_text())
    except Exception as e:
        logger.error("Failed to read %s: %s", files[0], e)
        return None
