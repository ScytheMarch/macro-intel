"""Regime Dashboard — posterior probabilities, transition matrix, uncertainty."""

from __future__ import annotations

import streamlit as st
import numpy as np
import pandas as pd


def render():
    st.markdown(
        '<h2>🧠 <span style="background:linear-gradient(135deg,#818cf8,#a78bfa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent">'
        'Regime Dashboard</span></h2>',
        unsafe_allow_html=True,
    )

    from macro_intel.data import cache

    run = cache.get_latest_model_run()
    if not run:
        st.warning("No model results found. Run `macro-intel fit` from the CLI first.")
        st.code("macro-intel fetch\nmacro-intel fit", language="bash")
        return

    st.caption(f"Latest run: {run['timestamp']} · Countries: {run['countries']} · "
               f"Regimes: {run['n_regimes']} · Features: {run['n_features']}")

    # Load InferenceData and re-run forward-backward
    idata_path = run.get("artifact")
    if not idata_path:
        st.error("No model artifact found.")
        return

    try:
        from macro_intel.data.feature_panel import build_panel, standardize_panel, PanelConfig
        from macro_intel.config.indicators import REGIME_FEATURES
        from macro_intel.models.regime_hmm import fit_regime_model
        from macro_intel.models.priors import RegimePriors
        import arviz as az

        countries = run["countries"].split(",")

        # Rebuild panel and get result from cache
        # For display, we show the stored model metadata
        st.subheader("Current Regime State")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Model Type", run["model_type"].upper())
        with col2:
            st.metric("MCMC Draws", f"{run['draws']:,}")
        with col3:
            st.metric("Countries", run["countries"])

        # Load and display InferenceData summary
        try:
            idata = az.from_netcdf(idata_path)

            st.subheader("Posterior Summary")
            summary = az.summary(idata, var_names=["P", "pi0"], round_to=3)
            st.dataframe(summary, use_container_width=True)

            st.subheader("Transition Matrix (Posterior Mean)")
            P = idata.posterior["P"].mean(dim=["chain", "draw"]).values
            labels = [f"Regime {i}" for i in range(P.shape[0])]
            P_df = pd.DataFrame(P, index=labels, columns=labels)
            st.dataframe(P_df.style.format("{:.3f}").background_gradient(cmap="Blues"),
                        use_container_width=True)

        except Exception as e:
            st.info(f"Could not load InferenceData: {e}")
            st.caption("Run the model to generate posterior data.")

    except Exception as e:
        st.error(f"Error loading model results: {e}")
