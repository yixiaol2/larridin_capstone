# Dashboard Spec

The Streamlit dashboard is a local research interface for exploring whether AI adoption signals relate to future company performance. It does not call live APIs, require a database, expose secrets, claim causality, or present investment advice.

Run locally:

```bash
streamlit run src/ai_impact_research/dashboard/app.py
```

Default inputs:

- `data/processed/analytic_panel.csv`
- `data/processed/analysis/ic_summary.csv`
- `data/processed/analysis/ic_by_quarter.csv`
- `data/processed/analysis/regression_results.csv`
- `data/processed/analysis/backtest_metrics.csv`
- `data/processed/analysis/backtest_quintile_returns.csv`
- `data/processed/analysis/backtest_long_short_returns.csv`

The sidebar allows local path overrides for the analytic panel and analysis output directory.

If files are missing, the dashboard shows friendly setup instructions:

```bash
python scripts/bootstrap_from_samples.py
python scripts/build_panel.py
python scripts/run_baseline_analysis.py
```

## Page 1: Overview

- Company count
- Quarter count
- Sector count and coverage table
- Sector coverage bar chart
- AI score distributions
- Missingness summary

## Page 2: Company Explorer

- Ticker selector
- Latest AI scores
- AI score history
- Financial outcome history
- Sector peer rank for a selected signal
- Caveats when company outcome data is missing

## Page 3: Signal Analysis

- Signal selector
- Outcome selector
- Signal/outcome scatter plot with sector coloring when available
- IC summary table
- IC by quarter chart
- Regression result table when available

## Page 4: Backtest

- Signal selector
- Quintile return table
- Quintile return chart
- Cumulative long-short chart
- Sharpe ratio, max drawdown, cumulative return, and rebalance count
- Prominent warning that the backtest is hypothetical research and not investment advice

## Page 5: Methodology

- Data sources
- Feature timing
- Look-ahead bias controls
- Limitations
- Responsible AI caveats
- Links/excerpts from project methodology docs

## Ticker-Level Report Generator

The deterministic report generator is available as a companion CLI workflow rather than a dashboard page in the current Streamlit structure:

```bash
python scripts/generate_company_report.py --ticker AIVA --panel data/processed/analytic_panel.csv --output reports/AIVA_report.md
```

The report generator uses local analytical-panel fields, peer/rank tools, optional saved backtest metrics, and optional saved LLM extraction evidence. A future dashboard integration can add a download button or report-preview page once the Streamlit runtime environment is stable.

## Implementation Notes

- Use Plotly for charts.
- Use Streamlit caching for dashboard data loading.
- Keep data loading in `dashboard/data_loader.py` pure enough for offline tests.
- Keep page code research-oriented and avoid hardcoded company conclusions.
- Surface missing analysis files without failing the whole dashboard.
