# Dashboard Spec (Real-Data Version — July 2026)

The Streamlit dashboard is a local research interface over the study's **real**
datasets. It reads processed parquet/CSV artifacts only — no live API calls, no
database, no secrets. It presents exploratory research and is not investment
advice.

Run locally:

```bash
make dashboard
# or: PYTHONPATH=src python3 -m streamlit run src/ai_impact_research/dashboard/app.py
```

Data inputs (all produced by the pipeline — see `HANDOFF.md` §4):

- `data/processed/analysis_table_v4.parquet` — company × signals × outcomes ×
  controls × AI value-chain category
- `data/processed/analysis_crosssection.parquet` — names/sectors/identifiers
- `data/processed/analysis/controls_regressions.csv` — specification-ladder results
- `data/processed/hiring/<snapshot>/company_hiring_signal.parquet` — monthly hiring signal

Data access lives in `dashboard/real_data.py` (cached loaders). The legacy
`data_loader.py` remains only to serve the original synthetic-sample tests.

## Pages

1. **Home** (`app.py`) — status metrics and the headline finding.
2. **Overview** — variable coverage table (with missingness reasons), sector
   coverage, distributions of maturity and concreteness.
3. **Company Explorer** — ticker selector → all signals (Larridin pillars,
   concreteness, investment, hiring), outcomes, and sector-percentile ranks.
4. **Signal Analysis** — interactive signal × outcome scatter with OLS trend,
   live Spearman IC, full IC table.
5. **Results** (file `4_Backtest.py`) — specification-ladder table from the
   saved regression results, concreteness/maturity sorts, value-chain
   heterogeneity, headline callout.
6. **Methodology** — design, signal construction, the validation stack
   (classifier agreement, evidence verification, reliability, placebo /
   permutation / leave-one-sector-out / rerun-stability), limitations,
   disclaimer.

## Implementation notes

- Plotly for charts; Streamlit caching (`st.cache_data`) for all loads.
- Pages bootstrap `sys.path` so the app runs from the repo root.
- Keep page code thin; anything reusable belongs in `real_data.py`.
- Every results view carries the exploratory-research caveat.
