# Data Directory

All collected and processed data **is tracked in git** (team decision, July
2026) so teammates can reproduce the analysis without API keys. `.env` and
credentials are never committed.

Layout:

- `data/raw/` — immutable exports as collected: `larridin/<date>/` (Supabase
  snapshot, 21 tables), `exa/<snapshot>/` (job-posting searches, June & July),
  SEC caches.
- `data/processed/` — everything the analysis reads:
  - `larridin/scores_flat.parquet` — deduped companies + flattened `aiScores`
  - `universe/universe.parquet` — Larridin ∪ S&P 500 with ticker + CIK
  - `market/forward_returns.parquet` — forward returns from t0 = 2026-01-19
  - `hiring/<snapshot>/company_hiring_signal.parquet` — builder/AI rates
  - `filings/filings_signals.parquet` — 10-K LLM signals (filings-v2)
  - `fundamentals/q1_outcomes.parquet`, `fundamentals/controls.parquet`
  - `analysis_table_v3/v4.parquet` — final regression tables (v4 adds the
    value-chain category)
  - `analysis/controls_regressions.csv` — specification-ladder results
- `data/samples/` — synthetic CSVs from the original scaffold (smoke tests
  only; not real data).

Provenance and run order for every artifact: `HANDOFF.md` §4.
