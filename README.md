# Larridin × CMU AI Capstone

Research project testing whether **AI-adoption signals predict public-company
performance**. We combine Larridin's AI Transformation Tracker scores with two
signal families we built from primary sources (10-K disclosure signals, AI-hiring
intensity from job postings), link them to market and SEC fundamental outcomes,
and run a controlled cross-sectional analysis.

> ### 👉 New to this repo? Read [`HANDOFF.md`](HANDOFF.md) first.
> It is the current-state guide: the data, the pipeline, the keys you need, and
> the results. The files under `docs/` describe the **original scaffold design**
> and are partly stale.

## Headline result (July 2026)

**Narrative concreteness — whether a company's 10-K reports named, deployed AI
use cases with quantified results — predicts Q1-2026 revenue growth through
sector, size, and momentum controls** (+8.7pp low→high, p = 0.007; passes FDR,
placebo/permutation/leave-one-sector-out/rerun-stability checks). Composite
adoption scores capture the phenomenon unconditionally but attenuate under a
size control. No signal predicts risk-adjusted returns (consistent with market
efficiency); margins show no effect. AI-infrastructure suppliers outperformed
sector/size-matched peers by ~37pp over the window.

Full write-up: **`reports/paper/main.tex`** (compiles with `tectonic`; 12-page
working draft with appendix).

## What's here

- **Data pipeline** (`scripts/`, run order in HANDOFF §4): Larridin snapshot →
  cleaning/dedup → universe + ticker/CIK → prices/returns → hiring collection +
  LLM classification (June & July snapshots) → 10-K signal extraction → SEC
  fundamentals → controls → regression suite.
- **Analysis artifacts** (`data/processed/`): `analysis_table_v3/v4.parquet`
  (company × signals × outcomes × controls × value-chain category),
  `analysis/controls_regressions.csv` (specification-ladder results).
- **Paper**: `reports/paper/` (LaTeX, real numbers throughout).
- **Presentation website** (`reports/site/`): static two-page site, no server needed —
  `index.html` (research narrative: finding, control-ladder "gauntlet", value chain,
  methodology) and `explore.html` (interactive Company Explorer: per-company signals,
  auto-generated insights, signal map, hiring movers). Open directly in a browser.
- **Interactive dashboard** (real data, Streamlit): see below.
- **Decks**: `reports/AI_Signals_Progress.pptx` (June), `reports/Weekly_Update.pptx` (July).

## Run the dashboard

```bash
make dashboard
# or: PYTHONPATH=src python3 -m streamlit run src/ai_impact_research/dashboard/app.py
```

Pages: Overview (coverage) · Company Explorer (per-ticker signals & peer ranks) ·
Signal Analysis (interactive scatter + IC) · Results (regressions, sorts,
heterogeneity) · Methodology (validation stack, limitations).

## Setup

Python 3.10+ (3.11 for the scaffold test suite). Install:

```bash
pip install -e ".[dev]"        # or: uv sync --all-extras
pip install yfinance           # pipeline dependency
cp .env.example .env           # then fill in keys — see HANDOFF §3
```

Required keys (never committed): `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`
(read Larridin), `EXA_API_KEY` (hiring collection), `OPENROUTER_API_KEY` (LLM
scoring), `SEC_USER_AGENT` (SEC EDGAR).

## Test commands

```bash
make test      # pytest
make lint      # ruff
```

## Data & secrets policy

- Never commit API keys or credentials (`.env` is gitignored).
- Treat Larridin's data as client-confidential; the repo is private.
- Every feature preserves an observation / `available_at` timestamp.
- Exploratory research — not investment advice; label hypothetical outputs.

## Repo structure

```text
HANDOFF.md                  # START HERE — current-state guide
reports/paper/              # LaTeX paper (main.tex → main.pdf)
scripts/                    # pipeline + analysis entry points (HANDOFF §4)
src/ai_impact_research/     # package; dashboard/ now serves REAL data
  llm/prompts/              # versioned prompts (jobclass-v1, filings-v2)
data/                       # raw + processed (real data gitignored on public forks)
docs/                       # original scaffold design docs (partly stale)
tests/                      # scaffold pytest suite (unchanged, green)
```
