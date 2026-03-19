"""Drift Monitor — Evidently-powered distributional shift detection with educational context."""

from __future__ import annotations

import streamlit as st


def render():
    from macro_intel.app.styles import (
        glass_card, section_header, badge, metric_card,
        TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, GREEN, RED, YELLOW, GRAY,
    )
    from macro_intel.data import cache
    from macro_intel.data.feature_panel import build_panel, PanelConfig

    st.markdown(
        '<h2 style="margin:0 0 4px 0;font-weight:800;letter-spacing:-0.5px">'
        '🔍 <span style="background:linear-gradient(135deg,#818cf8,#a78bfa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent">'
        'Drift Monitor</span></h2>'
        f'<div style="color:{TEXT_MUTED};font-size:0.78em;letter-spacing:0.3px;'
        f'margin-bottom:4px">Feature drift detection · Data quality monitoring</div>',
        unsafe_allow_html=True,
    )

    # Educational intro
    with st.expander("ℹ️ What is drift and why does it matter?", expanded=False):
        st.markdown("""
**Drift means the economy is behaving differently than it used to.**

Imagine you track your daily commute time for a year. If suddenly your commute starts taking
30 minutes longer every day, that's "drift" — the pattern has shifted. This tool does the
same thing for economic indicators.

**How it works:**
1. We define a **reference window** (e.g., the past 12 months ending 3 months ago) — this is "normal"
2. We define a **current window** (e.g., the last 3 months) — this is "now"
3. We use statistical tests to check: **is "now" significantly different from "normal"?**

**Why does this matter?**
- **Drift detected** 🔴 = Economic conditions are changing significantly. Models trained on old data
  may not work well. Portfolio strategies may need updating.
- **No drift** 🟢 = The economy is behaving consistently with recent history. Existing models
  and strategies remain reliable.

**Per-feature drift** tells you exactly WHICH indicators are shifting — is it inflation accelerating?
Labor markets weakening? Credit conditions tightening?

**Data quality** checks for missing values, stale data, and anomalies that could give misleading signals.
        """)

    test_date, test_val = cache.get_latest("UNRATE", "USA")
    if test_val is None:
        st.info("No data available. Go to **Regime Dashboard** and click **Fetch Data** first.")
        return

    # ── Controls ──────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        ref_months = st.number_input(
            "Reference Window (months)", 6, 36, 12,
            help="How many months of 'normal' history to compare against",
        )
    with col2:
        cur_months = st.number_input(
            "Current Window (months)", 1, 12, 3,
            help="How many recent months to check for changes",
        )
    with col3:
        country = st.selectbox("Country", ["USA"])

    st.markdown(
        f'<div style="color:{TEXT_DIM};font-size:0.82em;margin-bottom:12px">'
        f'Comparing the <b>last {cur_months} months</b> against the <b>preceding {ref_months} months</b>. '
        f'If the recent data looks statistically different, drift is detected.</div>',
        unsafe_allow_html=True,
    )

    if st.button("🔍 Run Drift Analysis", type="primary"):
        with st.spinner("Building feature panel..."):
            panel = build_panel(PanelConfig(countries=[country]))

        if panel.empty:
            st.error("No data in panel.")
            return

        # ── Feature Drift ─────────────────────────────────────────────────
        st.markdown(section_header("Feature Drift Analysis"), unsafe_allow_html=True)

        with st.spinner("Running statistical drift detection..."):
            try:
                from macro_intel.monitoring.drift import compute_feature_drift, DriftConfig

                drift_config = DriftConfig(
                    reference_months=ref_months,
                    current_months=cur_months,
                    country=country,
                )
                drift_result = compute_feature_drift(panel, drift_config)

                # Results cards
                d1, d2, d3 = st.columns(3)
                drift_detected = drift_result.dataset_drift
                with d1:
                    color = RED if drift_detected else GREEN
                    icon = "🔴" if drift_detected else "🟢"
                    label = "Drift Detected — Conditions Changing" if drift_detected else "No Drift — Conditions Stable"
                    st.markdown(
                        metric_card("Overall Verdict", f"{icon} {'DRIFT' if drift_detected else 'STABLE'}",
                                    color=color, border_left=color,
                                    sublabel=label),
                        unsafe_allow_html=True,
                    )
                with d2:
                    n_drifted = drift_result.n_drifted_features
                    n_total = drift_result.n_total_features
                    st.markdown(
                        metric_card("Indicators Shifting",
                                    f"{n_drifted} of {n_total}",
                                    sublabel=f"{n_drifted} indicators behaving differently than usual"),
                        unsafe_allow_html=True,
                    )
                with d3:
                    share = drift_result.drift_share
                    share_color = RED if share > 0.3 else YELLOW if share > 0.1 else GREEN
                    st.markdown(
                        metric_card("Drift Share", f"{share:.0%}",
                                    color=share_color,
                                    sublabel="% of indicators with significant change"),
                        unsafe_allow_html=True,
                    )

                # Interpretation
                if drift_detected:
                    st.markdown(
                        f'<div style="color:{TEXT_SECONDARY};font-size:0.88em;margin:12px 0;'
                        f'padding:12px 14px;background:rgba(239,68,68,0.08);border-radius:8px;'
                        f'border-left:3px solid {RED}">'
                        f'⚠️ <b>What this means:</b> The economy over the past {cur_months} months is behaving '
                        f'significantly differently from the prior {ref_months} months. '
                        f'{n_drifted} out of {n_total} indicators have shifted. '
                        f'This could signal a regime change, policy shift, or emerging risk. '
                        f'Check the per-feature breakdown below to see exactly what\'s changing.</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<div style="color:{TEXT_SECONDARY};font-size:0.88em;margin:12px 0;'
                        f'padding:12px 14px;background:rgba(34,197,94,0.08);border-radius:8px;'
                        f'border-left:3px solid {GREEN}">'
                        f'✅ <b>What this means:</b> Economic conditions over the past {cur_months} months '
                        f'are consistent with the prior {ref_months} months. No significant structural '
                        f'changes detected. Current models and strategies remain well-calibrated.</div>',
                        unsafe_allow_html=True,
                    )

                # Per-feature details
                if drift_result.feature_details:
                    st.markdown(section_header("Per-Feature Drift Scores"), unsafe_allow_html=True)
                    st.markdown(
                        f'<div style="color:{TEXT_DIM};font-size:0.82em;margin:-8px 0 12px 0">'
                        f'Each indicator below is tested individually. 🔴 = this specific indicator '
                        f'has shifted significantly. The drift score measures how different the distributions are '
                        f'(higher = more different).</div>',
                        unsafe_allow_html=True,
                    )

                    sorted_feats = sorted(
                        drift_result.feature_details.items(),
                        key=lambda x: x[1].get("drift_score", 0), reverse=True,
                    )

                    for feat_name, feat_data in sorted_feats[:20]:
                        drifted = feat_data.get("drifted", False)
                        score = feat_data.get("drift_score", 0)
                        shift = feat_data.get("shift_magnitude", 0)
                        icon = "🔴" if drifted else "🟢"
                        color = RED if drifted else GREEN

                        # Show shift direction
                        shift_text = ""
                        if shift != 0:
                            shift_dir = "↑" if shift > 0 else "↓"
                            shift_text = (
                                f'<span style="color:{TEXT_DIM};font-size:0.75em;margin-left:8px">'
                                f'{shift_dir}{abs(shift):.1f}σ shift</span>'
                            )

                        st.markdown(
                            f'<div style="display:flex;align-items:center;gap:8px;'
                            f'padding:6px 12px;margin:2px 0;'
                            f'background:linear-gradient(135deg,rgba(255,255,255,0.02),transparent);'
                            f'border-radius:8px;border-left:3px solid {color}">'
                            f'<span style="font-size:0.85em">{icon}</span>'
                            f'<span style="color:{TEXT_PRIMARY};font-size:0.85em;font-weight:500;'
                            f'flex:1">{feat_name}{shift_text}</span>'
                            f'<span style="color:{TEXT_MUTED};font-size:0.78em">'
                            f'p={1.0 - score:.4f}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

            except Exception as e:
                st.error(f"Drift analysis failed: {e}")

        # ── Data Quality ──────────────────────────────────────────────────
        st.markdown(section_header("Data Quality Check"), unsafe_allow_html=True)
        st.markdown(
            f'<div style="color:{TEXT_DIM};font-size:0.82em;margin:-8px 0 12px 0">'
            f'Checks for missing values, stale data, and anomalies that could '
            f'give misleading signals.</div>',
            unsafe_allow_html=True,
        )

        with st.spinner("Running quality checks..."):
            try:
                from macro_intel.monitoring.data_quality import check_data_quality

                quality = check_data_quality(panel, country=country)

                q1, q2, q3 = st.columns(3)
                with q1:
                    st.markdown(
                        metric_card("Total Data Points", f"{quality.n_rows:,}",
                                    sublabel="Rows in the dataset"),
                        unsafe_allow_html=True,
                    )
                with q2:
                    st.markdown(
                        metric_card("Indicators Tracked", str(quality.n_columns),
                                    sublabel="Economic series being monitored"),
                        unsafe_allow_html=True,
                    )
                with q3:
                    missing_color = RED if quality.missing_pct > 30 else YELLOW if quality.missing_pct > 10 else GREEN
                    st.markdown(
                        metric_card("Data Gaps", f"{quality.missing_pct:.1f}%",
                                    color=missing_color, border_left=missing_color,
                                    sublabel="% of cells with missing values"),
                        unsafe_allow_html=True,
                    )

                if quality.columns_with_issues:
                    st.markdown(
                        f'<div style="color:{YELLOW};font-size:0.85em;margin-top:12px">'
                        f'⚠️ <b>Indicators with issues:</b> '
                        f'{", ".join(quality.columns_with_issues[:10])}'
                        f'<br><span style="color:{TEXT_DIM};font-size:0.9em">'
                        f'These may have excessive missing data, zero variance, or stale values.</span></div>',
                        unsafe_allow_html=True,
                    )

            except Exception as e:
                st.error(f"Quality check failed: {e}")

    else:
        # Show previous results if available
        try:
            from macro_intel.monitoring.reports import get_latest_monitoring_report
            report = get_latest_monitoring_report()
        except Exception:
            report = None

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
                    n_drifted = drift.get("drifted_features", 0)
                    n_total = drift.get("total_features", 0)
                    st.markdown(
                        glass_card(
                            f'<div style="color:{TEXT_MUTED};font-size:0.72em;text-transform:uppercase;'
                            f'letter-spacing:1.2px;font-weight:600;margin-bottom:8px">Feature Drift</div>'
                            f'<div style="color:{RED if detected else GREEN};font-size:1.4em;'
                            f'font-weight:700">{"🔴 Drift Detected" if detected else "🟢 No Drift"}</div>'
                            f'<div style="color:{TEXT_MUTED};font-size:0.82em;margin-top:6px">'
                            f'{n_drifted}/{n_total} features shifted</div>'
                            f'<div style="color:{TEXT_DIM};font-size:0.78em;margin-top:4px">'
                            f'{"Economy changing — review your strategy" if detected else "Conditions stable — models well-calibrated"}</div>',
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
                            f'{quality.get("n_rows", 0):,} data points · {quality.get("n_columns", 0)} indicators</div>',
                        ),
                        unsafe_allow_html=True,
                    )
        else:
            st.markdown(
                glass_card(
                    f'<div style="text-align:center;padding:20px">'
                    f'<div style="font-size:1.5em;margin-bottom:8px">🔍</div>'
                    f'<div style="color:{TEXT_PRIMARY};font-size:0.95em;font-weight:500">'
                    f'Click <b>Run Drift Analysis</b> above to check for changes</div>'
                    f'<div style="color:{TEXT_MUTED};font-size:0.82em;margin-top:6px">'
                    f'This will compare recent economic data against its own recent history '
                    f'to detect if anything is shifting significantly</div>'
                    f'</div>',
                    border_color="rgba(99,102,241,0.15)",
                ),
                unsafe_allow_html=True,
            )
