# HANDOFF — Start Here

This is the accurate, current-state guide to the project as of June 2026.
The other `docs/` files describe the **original scaffold design** and are partly
stale — trust this file and the scripts under `scripts/`.

---

## 1. TL;DR

We test whether **AI-adoption signals predict company financial performance**.
Larridin provides AI-adoption scores for public companies; we cleaned them,
linked them to markets, and built additional signals (hiring, filings). The work
so far is **data collection + signal extension**; the statistical analysis is
the next phase.

**Key reality to internalize:** Larridin's scores are a **single snapshot
(January 2026)** — there is no multi-quarter history. So this is currently a
**cross-sectional** study (Jan-2026 signals → subsequent outcomes), *not* the
multi-quarter IC/backtest the original scaffold docs assume.

---

## 2. The data reality (what Larridin actually has)

- Source: Larridin's Supabase project **`mbyyempsotonpklaoxzw`**, read via the
  service-role key over the PostgREST REST API (read-only).
- **562 public companies** scored. The scores live inside
  `company_pages.content` as a JSON object called **`aiScores`** — *not* as flat
  columns. Each company has three pillar dimensions (**adoption, proficiency,
  impact**), each with a 1–5 `score`, a label, weighted sub-dimensions,
  `confidence`, and quoted `evidence`; plus an overall **`maturityIndex`** (1–5)
  and `maturityStage`. All `assessedAt` ≈ 2026-01-18/19.
- The universe is mostly S&P 500 but includes ~14 private/subsidiary companies
  (Aldi, Publix, IKEA, etc.) that have scores but no tradable stock.

> ⚠️ The original `docs/04_DATA_DICTIONARY.md` describes an assumed
> `larridin_scores` table with `ai_adoption_score` columns. **That is not how
> the real data is shaped.** Use the flattened table we produce instead
> (`data/processed/larridin/scores_flat.parquet`).

---

## 3. Keys you need (`.env`, never committed)

Copy `.env.example` → `.env` and fill these in (ask the team — keys are shared
privately, not in git):

| Variable | Used for |
|---|---|
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | read Larridin's data via REST |
| `EXA_API_KEY` | collect job postings (hiring signal) |
| `OPENROUTER_API_KEY` | LLM classification/scoring (Larridin-provided; use cheap models) |
| `SEC_USER_AGENT` | SEC EDGAR (filings + fundamentals); set to a real contact email |

`DATABASE_URL` is **not** required — we access Larridin over REST, not Postgres.

---

## 4. The pipeline (scripts in run order)

All scripts are self-contained and idempotent (re-runnable; cached/skipped where
possible). Run from the repo root. Outputs go under `data/` (gitignored).

| # | Script | Produces |
|---|---|---|
| 1 | `export_larridin_snapshot.py` | Read-only export of all 21 Supabase tables → `data/raw/larridin/<date>/` |
| 2 | `flatten_larridin_scores.py` | Dedupe companies (567→542) + flatten `aiScores` → `data/processed/larridin/scores_flat.parquet` (+ `companies_clean`, `dedup_log`) |
| 3 | `build_universe_mapping.py` | Universe = Larridin ∪ S&P 500, with ticker + CIK → `data/processed/universe/universe.parquet` |
| 4 | `pull_prices_returns.py` | yfinance daily prices + forward returns from t0=2026-01-19 → `data/processed/market/forward_returns.parquet` |
| 5 | `build_analysis_crosssection.py` | Join scores + returns → `data/processed/analysis_crosssection.parquet` |
| 6 | `collect_hiring_exa.py --snapshot 2026-06` | Exa job-posting search, full universe → `data/raw/exa/<snapshot>/` |
| 7 | `classify_hiring_postings.py --snapshot 2026-06` | LLM-classify each posting → `data/processed/hiring/<snapshot>/company_hiring_signal.parquet` |
| 8 | `validate_job_classifier.py` | (QA) classifier vs Larridin's 657 labeled postings → agreement metrics |
| 9 | `extract_filings_signals.py --all` | 10-K → 3 filings signals (filings-v2 prompt) → `data/processed/filings/filings_signals.parquet` |
| 10 | `pull_sec_fundamentals.py` | SEC Q1-2026 fundamentals (outcome vars) → `data/processed/fundamentals/q1_outcomes.parquet` |

> ⚠️ **Not yet a committed script:** the final merge of all signals + outcomes
> into one analysis table (`analysis_table_v2.parquet`) and the
> signal-vs-outcome correlation matrix were done ad-hoc. Formalizing this into a
> script is a good first task for the next phase.

---

## 5. The signals we built

**Hiring (per company, a rate — not a 1–5 score):** search AI job postings via
Exa → classify each as AI-builder / user / leader / non-AI → company-level
`builder_rate` and `ai_rate`. Classifier prompt:
`src/ai_impact_research/llm/prompts/job_posting_classification.md`. Validated
against Larridin's 657 labeled postings (~90% agreement on the builder class).

**Filings (three 1–5 scores from 10-Ks):** `ai_investment_intensity`,
`ai_narrative_concreteness`, `ai_risk_disclosure_depth`, each with cited
evidence. Prompt: `src/ai_impact_research/llm/prompts/filings_ai_signals.md`
(version **filings-v2** — v1 understated AI makers like Nvidia; v2 credits AI
investment whether the company builds or buys AI).

**Models:** hiring classification uses a Haiku-class model; filings scoring uses
a Sonnet-class model (the harder judgment task). Both via OpenRouter — keep to
cheap-but-capable models; the full runs cost ~$10–12 each.

---

## 6. Preliminary findings & caveats (do NOT over-claim)

- Early pattern: AI signals (both Larridin's and ours) are **significantly
  associated with Q1 revenue growth**, but **not** with margin change or
  short-term stock returns — consistent across signal sources.
- ⚠️ **This is not yet a result.** It must be re-checked controlling for company
  **size and prior growth momentum** — high-growth firms tend to score high on
  AI *and* keep growing, so the relationship may be confounded. This control is
  the #1 next task.
- Single cross-section → no statistical power for a multi-period backtest yet.

---

## 7. Known limitations / gaps

- **Hiring samples are thin** (~half the companies have <5 usable postings,
  because Exa search depth is budget-limited to 25 results/company). A July
  snapshot + more Exa credit would help; also consider normalizing by company
  size (employee count from SEC is sparse — revenue is a usable denominator).
- **Filings:** `concreteness` is the strongest dimension; `risk` is nearly
  degenerate (most large firms disclose AI risk similarly).
- **Coverage:** hiring ≈ all tradable companies (536); filings = 478 (needs a
  Larridin score + a US 10-K, so foreign filers / acquired firms drop out).
- 14 private/subsidiary companies have scores but no market/financial outcomes.

---

## 8. Next steps

1. Formalize the final merge + analysis into a script; add size & momentum
   controls and multiple-testing correction; test the revenue-growth finding.
2. July hiring snapshot (second time point) — re-run scripts 6–7 with
   `--snapshot 2026-07`.
3. Press / news signal (free via GDELT; can backfill history with timestamps).
4. Earnings-call transcripts (deferred — would enrich the filings signal).
