"""Drift Monitor — Evidently-powered distributional shift detection."""

from __future__ import annotations

import streamlit as st


def render():
    from macro_intel.app.styles import (
        glass_card, section_header, badge, metric_card,
        TEXT_MUTED, TEXT_PRIMARY, GREEN, RED, YELLOW, GRAY,
    )
    from macro_intel.data import cache
    from macro_intel.data.feature_panel import build_panel, PanelConfig

    st.markdown(
        '<h2 style="margin:0 0 4px 0;font-weight:800;letter-spacing:-0.5px">'
        '🔍 <span style="background:linear-gradient(135deg,#818cf8,#a78bfa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent">'
        'Drift Monitor</span></h2>'
        f'<div style="color:{TEXT_MUTED};font-size:0.78em;letter-spacing:0.3px;'
        f'margin-bottom:16px">Feature drift detection · Data quality monitoring · '
        f'Powered by Evidently AI</div>',
        unsafe_allow_html=True,
    )

    test_date, test_val = cache.get_latest("UNRATE", "USA")
    if test_val is None:
        st.info("No data available. Go to **Regime Dashboard** and click **Fetch Data** first.")
        return

    # ── Controls ──────────────────────────────────────────────────────────
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
        st.markdown(section_header("Feature Drift Analysis"), unsafe_allow_html=True)

        with st.spinner("Running Evidently drift detection..."):
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

                # Results cards
                d1, d2, d3 = st.columns(3)
                drift_detected = drift_result.dataset_drift
                with d1:
                    color = RED if drift_detected else GREEN
                    icon = "🔴" if drift_detected else "🟢"
                    st.markdown(
                        metric_card("Dataset Drift", f"{icon} {'Yes' if drift_detected else 'No'}",
                                    color=color, border_left=color),
                        unsafe_allow_html=True,
                    )
                with d2:
                    st.markdown(
                        metric_card("Drifted Features",
                                    f"{drift_result.n_drifted_features}/{drift_result.n_total_features}",
                                    sublabel=f"Share: {drift_result.drift_share:.1%}"),
                        unsafe_allow_html=True,
                    )
                with d3:
                    st.markdown(
                        metric_card("Drift Share", f"{drift_result.drift_share:.1%}",
                                    color=RED if drift_result.drift_share > 0.3 else YELLOW if drift_result.drift_share > 0.1 else GREEN),
                        unsafe_allow_html=True,
                    )

                # Per-feature details
                if drift_result.feature_details:
                    st.markdown(section_header("Per-Feature Drift Scores"), unsafe_allow_html=True)

                    sorted_feats = sorted(
                        drift_result.feature_details.items(),
                        key=lambda x: x[1].get("drift_score", 0), reverse=True,
                    )

                    for feat_name, feat_data in sorted_feats[:20]:
                        drifted = feat_data.get("drifted", False)
                        score = feat_data.get("drift_score", 0)
                        icon = "🔴" if drifted else "🟢"
                        color = RED if drifted else GREEN

                        st.markdown(
                            f'<div style="display:flex;align-items:center;gap:8px;'
                            f'padding:6px 12px;margin:2px 0;'
                            f'background:linear-gradient(135deg,rgba(255,255,255,0.02),transparent);'
                            f'border-radius:8px;border-left:3px solid {color}">'
                            f'<span style="font-size:0.85em">{icon}</span>'
                            f'<span style="color:{TEXT_PRIMARY};font-size:0.85em;font-weight:500;'
                            f'flex:1">{feat_name}</span>'
                            f'<span style="color:{TEXT_MUTED};font-size:0.78em">'
                            f'score: {score:.4f}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                # Embed HTML report
                if drift_result.report_path:
                    with st.expander("Full Evidently Drift Report", expanded=False):
                        from pathlib import Path
                        html = Path(drift_result.report_path).read_text(encoding="utf-8")
                        st.components.v1.html(html, height=800, scrolling=True)

            except ImportError:
                st.error("Evidently not installed. Install with: `pip install evidently`")
            except Exception as e:
                st.error(f"Drift analysis failed: {e}")

        # ── Data Quality ──────────────────────────────────────────────────
        st.markdown(section_header("Data Quality"), unsafe_allow_html=True)

        with st.spinner("Running quality checks..."):
            try:
                from macro_intel.monitoring.data_quality import check_data_quality
                from macro_intel.config.settings import settings

                quality = check_data_quality(
                    panel, country=country,
                    output_path=settings.reports_dir / f"quality_{country}.html",
                )

                q1, q2, q3 = st.columns(3)
                with q1:
                    st.markdown(
                        metric_card("Rows", f"{quality.n_rows:,}"),
                        unsafe_allow_html=True,
                    )
                with q2:
                    st.markdown(
                        metric_card("Columns", str(quality.n_columns)),
                        unsafe_allow_html=True,
                    )
                with q3:
                    missing_color = RED if quality.missing_pct > 30 else YELLOW if quality.missing_pct > 10 else GREEN
                    st.markdown(
                        metric_card("Missing", f"{quality.missing_pct:.1f}%",
                                    color=missing_color, border_left=missing_color),
                        unsafe_allow_html=True,
                    )

                if quality.columns_with_issues:
                    st.markdown(
                        f'<div style="color:{YELLOW};font-size:0.85em;margin-top:12px">'
                        f'⚠️ Columns with issues: '
                        f'{", ".join(quality.columns_with_issues[:10])}</div>',
                        unsafe_allow_html=True,
                    )

                if quality.report_path:
                    with st.expander("Full Quality Report", expanded=False):
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
            st.markdown(
                f'<div style="color:{TEXT_MUTED};font-size:0.82em">'
                f'Last analysis: {report.get("timestamp", "N/A")}</div>',
                unsafe_allow_html=True,
            )

            col1, col2 = st.columns(2)
            with col1:
                drift = report.get("drift", {})
                if drift:
                    detected = drift.get("dataset_drift_detected", False)
                    st.markdown(
                        glass_card(
                            f'<div style="color:{TEXT_MUTED};font-size:0.72em;text-transform:uppercase;'
                            f'letter-spacing:1.2px;font-weight:600;margin-bottom:8px">Feature Drift</div>'
                            f'<div style="color:{RED if detected else GREEN};font-size:1.4em;'
                            f'font-weight:700">{"🔴 Drift Detected" if detected else "🟢 No Drift"}</div>'
                            f'<div style="color:{TEXT_MUTED};font-size:0.82em;margin-top:6px">'
                            f'{drift.get("drifted_features", 0)}/{drift.get("total_features", 0)} '
                            f'features drifted</div>',
                            border_color=f"{RED}44" if detected else f"{GREEN}44",
                        ),
                        unsafe_allow_html=True,
                    )
            with col2:
                quality = report.get("quality", {})
                if quality:
                    st.markdown(
                        glass_card(
                            f'<div style="color:{TEXT_MUTED};font-size:0.72em;text-transform:uppercase;'
                            f'letter-spacing:1.2px;font-weight:600;margin-bottom:8px">Data Quality</div>'
                            f'<div style="color:{TEXT_PRIMARY};font-size:1.4em;font-weight:700">'
                            f'{quality.get("missing_pct", 0):.1f}% Missing</div>'
                            f'<div style="color:{TEXT_MUTED};font-size:0.82em;margin-top:6px">'
                            f'{quality.get("n_rows", 0)} rows · {quality.get("n_columns", 0)} columns</div>',
                        ),
                        unsafe_allow_html=True,
                    )
        else:
            st.markdown(
                glass_card(
                    f'<div style="text-align:center;padding:20px">'
                    f'<div style="font-size:1.5em;margin-bottom:8px">🔍</div>'
                    f'<div style="color:{TEXT_PRIMARY};font-size:0.95em;font-weight:500">'
                    f'Click <b>Run Drift Analysis</b> to detect distributional shifts</div>'
                    f'<div style="color:{TEXT_MUTED};font-size:0.78em;margin-top:6px">'
                    f'Compares reference window vs current window using statistical tests</div>'
                    f'</div>',
                    border_color="rgba(99,102,241,0.15)",
                ),
                unsafe_allow_html=True,
            )
