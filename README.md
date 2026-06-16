# Larridin × CMU AI Capstone

Research project testing whether **AI-adoption signals predict future
public-company performance**. Larridin provides AI-adoption scores for public
companies; we clean them, link them to market and financial data, and build
additional evidence-based signals (hiring, filings) to study the relationship.

> ### 👉 New to this repo? Read [`HANDOFF.md`](HANDOFF.md) first.
> It is the accurate, current-state guide: what the real Larridin data looks
> like, the data-collection pipeline we built, the API keys you need, and the
> preliminary findings. The files under `docs/` describe the **original
> scaffold design** and are partly stale.

## What's actually here

- **Larridin AI scores** (cleaned/flattened from their Supabase) — three pillar
  dimensions (adoption, proficiency, impact) plus a maturity index, from a
  single January-2026 snapshot.
- **A 564-company universe** (Larridin ∪ S&P 500) mapped to ticker + CIK.
- **Market & fundamental outcomes** — stock prices / forward returns and
  Q1-2026 SEC fundamentals.
- **Two new signals we built** — AI hiring intensity (from job postings via Exa)
  and AI filing signals (from 10-Ks via LLM extraction).

## Real data pipeline

Scripts run from the repo root, in order (details + outputs in
[`HANDOFF.md`](HANDOFF.md)):

```text
export_larridin_snapshot → flatten_larridin_scores → build_universe_mapping
  → pull_prices_returns → build_analysis_crosssection
  → collect_hiring_exa → classify_hiring_postings        (hiring signal)
  → extract_filings_signals                              (filings signal)
  → pull_sec_fundamentals                                (outcomes)
```

Required keys (in `.env`, never committed): `SUPABASE_URL` +
`SUPABASE_SERVICE_ROLE_KEY` (read Larridin), `EXA_API_KEY` (hiring),
`OPENROUTER_API_KEY` (LLM scoring), `SEC_USER_AGENT` (SEC EDGAR).

## Setup

Python 3.11+ recommended. `uv` or plain `pip`:

```bash
uv sync --all-extras            # or: pip install -e ".[dev]"
cp .env.example .env            # then fill in the keys above
```

The pipeline scripts also use `requests`, `yfinance`, `python-dotenv`,
`pandas`, `pyarrow` (install via the above).

## Test commands

```bash
make test      # pytest
make lint      # ruff
```

## Original scaffold smoke-test (synthetic data)

The committed `data/samples/` are **synthetic** and only exercise the original
scaffold (panel builder, baseline analysis, dashboard). Not the real pipeline:

```bash
make sample-panel && make sample-analysis
```

## Data & secrets policy

- Never commit API keys, tokens, or database credentials (`.env` is gitignored).
- Real collected data lives under `data/` (gitignored). Treat Larridin's data as
  client-confidential — do not publish it outside the project.
- Every model feature preserves an observation / `available_at` timestamp.
- Label exploratory or hypothetical outputs clearly; do not present preliminary
  correlations as findings.

## Repo structure

```text
HANDOFF.md                 # START HERE — current-state guide
scripts/                   # data-collection pipeline (see HANDOFF) + scaffold entry points
src/ai_impact_research/     # Python package (ingestion, processing, analysis, llm, dashboard)
  llm/prompts/             # versioned LLM prompts (job_posting_classification, filings_ai_signals)
docs/                       # ORIGINAL scaffold design docs (partly stale — see HANDOFF)
data/                       # collected data + synthetic samples (real data gitignored)
infra/  configs/  tests/    # SQL schema, config, pytest suite
```
