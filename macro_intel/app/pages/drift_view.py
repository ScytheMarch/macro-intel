"""Drift Monitor — run Evidently drift and quality analysis on-the-fly."""

from __future__ import annotations

import streamlit as st


def render():
    st.markdown(
        '<h2>🔍 <span style="background:linear-gradient(135deg,#818cf8,#a78bfa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent">'
        'Drift Monitor</span></h2>',
        unsafe_allow_html=True,
    )

    from macro_intel.data import cache
    from macro_intel.data.feature_panel import build_panel, PanelConfig

    # Check data
    test_date, test_val = cache.get_latest("UNRATE", "USA")
    if test_val is None:
        st.info("No data available. Go to **Regime Dashboard** and click **Fetch Data** first.")
        return

    # Controls
    col1, col2, col3 = st.columns(3)
    with col1:
        ref_months = st.number_input("Reference Window (months)", 6, 36, 12)
    with col2:
        cur_months = st.number_input("Current Window (months)", 1, 12, 3)
    with col3:
        country = st.selectbox("Country", ["USA"])

    if st.button("🔍 Run Drift Analysis", type="primary"):
        with st.spinner("Building feature panel..."):
            panel = build_panel(PanelConfig(countries=[country]))

        if panel.empty:
            st.error("No data in panel.")
            return

        # ── Feature Drift ─────────────────────────────────────────────────
        with st.spinner("Running feature drift analysis..."):
            try:
                from macro_intel.monitoring.drift import compute_feature_drift, DriftConfig
                from macro_intel.config.settings import settings

                drift_config = DriftConfig(
                    reference_months=ref_months,
                    current_months=cur_months,
                    country=country,
                )
                drift_result = compute_feature_drift(
                    panel, drift_config,
                    output_path=settings.reports_dir / f"drift_{country}.html",
                )

                col1, col2, col3 = st.columns(3)
                with col1:
                    color = "🔴" if drift_result.dataset_drift else "🟢"
                    st.metric(f"{color} Drift Detected", str(drift_result.dataset_drift))
                with col2:
                    st.metric("Drifted Features",
                              f"{drift_result.n_drifted_features}/{drift_result.n_total_features}")
                with col3:
                    st.metric("Drift Share", f"{drift_result.drift_share:.1%}")

                # Top drifted features
                if drift_result.feature_details:
                    st.subheader("Feature Drift Details")
                    sorted_features = sorted(
                        drift_result.feature_details.items(),
                        key=lambda x: x[1].get("drift_score", 0),
                        reverse=True,
                    )
                    for feat_name, feat_data in sorted_features[:15]:
                        drifted = feat_data.get("drifted", False)
                        score = feat_data.get("drift_score", 0)
                        icon = "🔴" if drifted else "🟢"
                        st.text(f"{icon} {feat_name:.<40s} score={score:.4f}")

                # Embed HTML report
                if drift_result.report_path:
                    st.subheader("Full Evidently Report")
                    from pathlib import Path
                    html = Path(drift_result.report_path).read_text(encoding="utf-8")
                    st.components.v1.html(html, height=800, scrolling=True)

            except ImportError:
                st.error("Evidently not installed. Install with: `pip install evidently`")
            except Exception as e:
                st.error(f"Drift analysis failed: {e}")

        # ── Data Quality ──────────────────────────────────────────────────
        st.divider()
        with st.spinner("Running data quality checks..."):
            try:
                from macro_intel.monitoring.data_quality import check_data_quality
                from macro_intel.config.settings import settings

                quality = check_data_quality(
                    panel, country=country,
                    output_path=settings.reports_dir / f"quality_{country}.html",
                )

                st.subheader("Data Quality")
                q1, q2, q3 = st.columns(3)
                q1.metric("Rows", quality.n_rows)
                q2.metric("Columns", quality.n_columns)
                q3.metric("Missing %", f"{quality.missing_pct:.1f}%")

                if quality.columns_with_issues:
                    st.warning(f"**Columns with issues:** {', '.join(quality.columns_with_issues[:10])}")

                    for col_name in quality.columns_with_issues[:10]:
                        stats = quality.summary.get(col_name, {})
                        issues = stats.get("issues", [])
                        st.text(f"  ⚠️ {col_name}: {', '.join(issues)}")

                # Embed quality report
                if quality.report_path:
                    st.subheader("Full Quality Report")
                    from pathlib import Path
                    html = Path(quality.report_path).read_text(encoding="utf-8")
                    st.components.v1.html(html, height=800, scrolling=True)

            except ImportError:
                st.error("Evidently not installed.")
            except Exception as e:
                st.error(f"Quality check failed: {e}")

    else:
        # Show previous results if available
        from macro_intel.monitoring.reports import get_latest_monitoring_report

        report = get_latest_monitoring_report()
        if report:
            st.caption(f"Last analysis: {report.get('timestamp', 'N/A')}")

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
                else:
                    st.info("No previous drift data")

            with col2:
                st.subheader("Data Quality")
                quality = report.get("quality", {})
                if quality:
                    st.metric("Missing %", f"{quality.get('missing_pct', 0):.1f}%")
                    issues = quality.get("columns_with_issues", [])
                    if issues:
                        st.write(f"**Issues in:** {', '.join(issues[:8])}")
                else:
                    st.info("No previous quality data")
        else:
            st.caption("Click **Run Drift Analysis** to analyze your data for distributional shifts.")
