"""Typer CLI for macro-intel pipeline operations.

Commands:
    macro-intel fetch     — Fetch data from FRED, World Bank, and market sources
    macro-intel panel     — Build and inspect the feature panel
    macro-intel fit       — Fit the Bayesian regime model
    macro-intel graphs    — Generate PyVis network graphs
    macro-intel drift     — Run Evidently drift analysis
    macro-intel report    — Print regime summary and monitoring status
    macro-intel ui        — Launch Streamlit dashboard
"""

from __future__ import annotations

import logging
import sys

import typer

app = typer.Typer(
    name="macro-intel",
    help="Probabilistic macroeconomic intelligence system",
    add_completion=False,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("macro_intel")


@app.command()
def fetch(
    countries: str = typer.Option("USA", help="Comma-separated ISO3 country codes"),
    lookback: int = typer.Option(10, help="Years of history to fetch"),
    skip_wb: bool = typer.Option(False, help="Skip World Bank data"),
    skip_market: bool = typer.Option(False, help="Skip market index data"),
):
    """Fetch data from all sources into the local cache."""
    from macro_intel.config.indicators import get_fred_indicators, get_wb_indicators
    from macro_intel.config.countries import COUNTRIES
    from macro_intel.data import cache, fred_client, worldbank_client, market_client

    country_list = [c.strip() for c in countries.split(",")]
    typer.echo(f"🔄 Fetching data for: {country_list} ({lookback}y lookback)")

    # FRED data (US)
    if "USA" in country_list:
        fred_ids = list(get_fred_indicators().keys())
        typer.echo(f"  📊 FRED: {len(fred_ids)} indicators...")
        data = fred_client.fetch_multiple(fred_ids, lookback_years=lookback)
        for sid, df in data.items():
            if not df.empty:
                cache.upsert_observations(sid, df, country="USA")
                info = fred_client.get_series_info(sid)
                cache.upsert_metadata(sid, country="USA", source="fred", **info)
        typer.echo(f"  ✅ FRED: {sum(1 for d in data.values() if not d.empty)}/{len(fred_ids)} fetched")

    # World Bank data
    if not skip_wb:
        wb_ids = list(get_wb_indicators().keys())
        wb_countries = [c for c in country_list if c in COUNTRIES]
        typer.echo(f"  🌍 World Bank: {len(wb_ids)} indicators × {len(wb_countries)} countries...")
        for ind_code in wb_ids:
            df = worldbank_client.fetch_indicator(ind_code, wb_countries, start_year=2000)
            if not df.empty:
                for country in df["country"].unique():
                    country_data = df[df["country"] == country][["date", "value"]]
                    country_data = country_data.set_index("date")
                    cache.upsert_observations(ind_code, country_data, country=country)
                    cache.upsert_metadata(ind_code, country=country, source="worldbank")
        typer.echo(f"  ✅ World Bank: done")

    # Market indices
    if not skip_market:
        typer.echo(f"  📈 Market indices...")
        for country in country_list:
            if country in COUNTRIES:
                df = market_client.fetch_index_prices(country, period=f"{lookback}y")
                if not df.empty:
                    cache.upsert_observations(f"MKT_{country}", df, country=country)
                    typer.echo(f"    {country}: {len(df)} days")
        typer.echo(f"  ✅ Market data: done")

    typer.echo("✅ Fetch complete")


@app.command()
def panel(
    countries: str = typer.Option("USA", help="Comma-separated ISO3 codes"),
    start: str = typer.Option("2000-01-01", help="Panel start date"),
):
    """Build and display feature panel summary."""
    from macro_intel.data.feature_panel import build_panel, get_panel_summary, PanelConfig

    country_list = [c.strip() for c in countries.split(",")]
    config = PanelConfig(countries=country_list, start_date=start)
    p = build_panel(config)

    summary = get_panel_summary(p)
    typer.echo(f"\n📊 Feature Panel Summary:")
    typer.echo(f"  Rows: {summary['n_rows']}")
    typer.echo(f"  Features: {summary['n_features']}")
    typer.echo(f"  Countries: {summary['countries']}")
    typer.echo(f"  Date range: {summary.get('date_range', 'N/A')}")
    typer.echo(f"  Missing: {summary.get('missing_pct', 0):.1f}%")

    if summary.get("obs_per_country"):
        for c, n in summary["obs_per_country"].items():
            typer.echo(f"    {c}: {n} observations")


@app.command()
def fit(
    countries: str = typer.Option("USA", help="Comma-separated ISO3 codes"),
    draws: int = typer.Option(2000, help="MCMC draws"),
    tune: int = typer.Option(1000, help="MCMC tuning steps"),
    chains: int = typer.Option(4, help="MCMC chains"),
):
    """Fit the Bayesian regime model."""
    from macro_intel.config.settings import settings
    from macro_intel.data.feature_panel import build_panel, standardize_panel, PanelConfig
    from macro_intel.config.indicators import REGIME_FEATURES
    from macro_intel.models.priors import RegimePriors
    from macro_intel.models.regime_hmm import fit_regime_model
    from macro_intel.data import cache

    country_list = [c.strip() for c in countries.split(",")]
    typer.echo(f"🧠 Fitting regime model for: {country_list}")
    typer.echo(f"   Config: draws={draws}, tune={tune}, chains={chains}")

    # Build panel
    config = PanelConfig(countries=country_list)
    panel = build_panel(config)
    if panel.empty:
        typer.echo("❌ No data in panel. Run 'macro-intel fetch' first.")
        raise typer.Exit(1)

    panel_z = standardize_panel(panel)

    # Configure priors
    priors = RegimePriors(draws=draws, tune=tune, chains=chains)

    # Fit
    save_path = settings.model_dir / "regime_hmm_latest.nc"
    result = fit_regime_model(
        panel_z,
        countries=country_list,
        feature_cols=[c for c in REGIME_FEATURES if c in panel_z.columns],
        priors=priors,
        save_path=save_path,
    )

    # Log the run
    cache.log_model_run(
        model_type="regime_hmm",
        countries=country_list,
        n_features=len(result.feature_names),
        n_regimes=len(result.regime_labels),
        draws=draws,
        artifact=str(save_path),
    )

    typer.echo(f"\n✅ Model fitted successfully")
    typer.echo(f"   Regimes: {result.regime_labels}")
    typer.echo(f"   Current regime: {result.regime_labels[result.regime_map[-1]]}")
    typer.echo(f"   Uncertainty: {result.uncertainty:.3f}")
    typer.echo(f"   Saved to: {save_path}")

    # Print transition matrix
    typer.echo(f"\n   Transition matrix:")
    for i, label in enumerate(result.regime_labels):
        row = " ".join(f"{p:.2f}" for p in result.transition_matrix[i])
        typer.echo(f"     {label:15s} → {row}")


@app.command()
def graphs(
    countries: str = typer.Option("USA", help="Comma-separated ISO3 codes"),
):
    """Generate PyVis network graphs."""
    from macro_intel.config.settings import settings
    from macro_intel.analytics.correlations import build_indicator_correlation_matrix
    from macro_intel.graphs.macro_dependency import build_dependency_graph

    typer.echo("🕸️  Generating network graphs...")

    # Macro dependency graph
    corr = build_indicator_correlation_matrix()
    if not corr.empty:
        path = build_dependency_graph(
            corr,
            output_path=settings.reports_dir / "macro_dependency.html",
        )
        typer.echo(f"  ✅ Macro dependency: {path}")
    else:
        typer.echo("  ⚠️  Insufficient data for dependency graph")

    typer.echo("✅ Graphs complete")


@app.command()
def drift(
    country: str = typer.Option("USA", help="Country to analyze"),
    ref_months: int = typer.Option(12, help="Reference window months"),
    cur_months: int = typer.Option(3, help="Current window months"),
):
    """Run Evidently drift and data quality analysis."""
    from macro_intel.config.settings import settings
    from macro_intel.data.feature_panel import build_panel, PanelConfig
    from macro_intel.monitoring.drift import compute_feature_drift, DriftConfig
    from macro_intel.monitoring.data_quality import check_data_quality
    from macro_intel.monitoring.reports import save_monitoring_summary

    typer.echo(f"🔍 Running drift analysis for {country}...")

    panel = build_panel(PanelConfig(countries=[country]))
    if panel.empty:
        typer.echo("❌ No data. Run 'macro-intel fetch' first.")
        raise typer.Exit(1)

    # Feature drift
    drift_config = DriftConfig(
        reference_months=ref_months,
        current_months=cur_months,
        country=country,
    )
    drift_result = compute_feature_drift(
        panel, drift_config,
        output_path=settings.reports_dir / f"drift_{country}.html",
    )
    typer.echo(f"  Drift detected: {drift_result.dataset_drift}")
    typer.echo(f"  Drifted features: {drift_result.n_drifted_features}/{drift_result.n_total_features}")

    # Data quality
    quality_result = check_data_quality(
        panel, country=country,
        output_path=settings.reports_dir / f"quality_{country}.html",
    )
    typer.echo(f"  Missing data: {quality_result.missing_pct}%")
    if quality_result.columns_with_issues:
        typer.echo(f"  Issues in: {quality_result.columns_with_issues[:5]}")

    # Save summary
    summary_path = save_monitoring_summary(drift_result, quality_result, country)
    typer.echo(f"  📄 Summary: {summary_path}")


@app.command()
def report():
    """Print current regime summary and monitoring status."""
    from macro_intel.data import cache
    from macro_intel.monitoring.reports import get_latest_monitoring_report

    typer.echo("📋 Macro-Intel Status Report")
    typer.echo("=" * 50)

    # Latest model run
    run = cache.get_latest_model_run()
    if run:
        typer.echo(f"\n🧠 Latest Model Run:")
        typer.echo(f"   Timestamp: {run['timestamp']}")
        typer.echo(f"   Countries: {run['countries']}")
        typer.echo(f"   Features: {run['n_features']}")
        typer.echo(f"   Regimes: {run['n_regimes']}")
        typer.echo(f"   Draws: {run['draws']}")
        typer.echo(f"   Artifact: {run['artifact']}")
    else:
        typer.echo("\n⚠️  No model runs found. Run 'macro-intel fit' first.")

    # Latest monitoring
    monitoring = get_latest_monitoring_report()
    if monitoring:
        typer.echo(f"\n🔍 Latest Monitoring ({monitoring.get('timestamp', '?')}):")
        drift = monitoring.get("drift", {})
        if drift:
            typer.echo(f"   Drift detected: {drift.get('dataset_drift_detected', '?')}")
            typer.echo(f"   Drifted: {drift.get('drifted_features', 0)}/{drift.get('total_features', 0)}")
        quality = monitoring.get("quality", {})
        if quality:
            typer.echo(f"   Missing: {quality.get('missing_pct', 0)}%")
    else:
        typer.echo("\n⚠️  No monitoring reports. Run 'macro-intel drift' first.")


@app.command()
def ui():
    """Launch the Streamlit dashboard."""
    import subprocess
    app_path = str(__import__("macro_intel").__path__[0] / "app" / "streamlit_app.py")
    # Fallback
    from pathlib import Path
    app_path = str(Path(__file__).parent / "streamlit_app.py")
    typer.echo(f"🚀 Launching Streamlit dashboard...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path], check=True)


if __name__ == "__main__":
    app()
