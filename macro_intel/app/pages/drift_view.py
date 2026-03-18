"""Drift Monitor — view Evidently drift and quality reports."""

from __future__ import annotations

import streamlit as st
from pathlib import Path


def render():
    st.markdown(
        '<h2>🔍 <span style="background:linear-gradient(135deg,#818cf8,#a78bfa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent">'
        'Drift Monitor</span></h2>',
        unsafe_allow_html=True,
    )

    from macro_intel.config.settings import settings
    from macro_intel.monitoring.reports import get_latest_monitoring_report

    # Show latest summary
    report = get_latest_monitoring_report()
    if report:
        st.caption(f"Latest report: {report.get('timestamp', 'N/A')}")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Feature Drift")
            drift = report.get("drift", {})
            if drift:
                detected = drift.get("dataset_drift_detected", False)
                color = "🔴" if detected else "🟢"
                st.metric(f"{color} Drift Detected", str(detected))
                st.metric("Drifted Features",
                          f"{drift.get('drifted_features', 0)}/{drift.get('total_features', 0)}")
                st.metric("Drift Share", f"{drift.get('drift_share', 0):.1%}")

                top = drift.get("top_drifted", [])
                if top:
                    st.write("**Top Drifted Features:**")
                    for item in top[:5]:
                        st.write(f"  • {item['feature']}: score={item.get('drift_score', 0):.3f}")
            else:
                st.info("No drift data available")

        with col2:
            st.subheader("Data Quality")
            quality = report.get("quality", {})
            if quality:
                st.metric("Rows", quality.get("n_rows", 0))
                st.metric("Columns", quality.get("n_columns", 0))
                st.metric("Missing %", f"{quality.get('missing_pct', 0):.1f}%")

                issues = quality.get("columns_with_issues", [])
                if issues:
                    st.write(f"**Columns with issues:** {', '.join(issues[:8])}")
            else:
                st.info("No quality data available")
    else:
        st.warning("No monitoring reports found. Run `macro-intel drift` first.")
        st.code("macro-intel drift", language="bash")

    # Embed HTML reports
    st.divider()
    reports_dir = settings.reports_dir

    report_files = {
        "Feature Drift Report": reports_dir / "drift_USA.html",
        "Data Quality Report": reports_dir / "quality_USA.html",
    }

    available = {name: path for name, path in report_files.items() if path.exists()}
    if available:
        selected = st.selectbox("View Detailed Report", list(available.keys()))
        if selected and selected in available:
            html = available[selected].read_text(encoding="utf-8")
            st.components.v1.html(html, height=800, scrolling=True)
