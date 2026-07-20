# HANDOFF — Start Here

This is the accurate, current-state guide to the project as of July 2026.
The other `docs/` files describe the **original scaffold design** and are partly
stale — trust this file and the scripts under `scripts/`.

---

## 1. TL;DR

We test whether **AI-adoption signals predict company financial performance**.
Larridin provides AI-adoption scores for public companies; we cleaned them,
linked them to markets, built additional signals (hiring, filings), and ran the
full controlled analysis. **Status (July 2026): analysis complete, paper
drafted (`reports/paper/main.tex`), dashboard serves real data, presentation
site live at <https://yixiaol2.github.io/larridin_capstone/> (source in
`reports/site/`, published via the `gh-pages` branch).** Headline:
disclosure concreteness predicts revenue growth through sector/size/momentum
controls (+8.0pp, p=0.009); composite scores attenuate under size; returns and
margins show no effects; see §6.

> **⚠️ Analysis base = ex-5 (client request, 2026-07-14).** At Ameya's request,
> the paper's main analysis **excludes the five largest AI-semiconductors**
> (NVDA, AVGO, AMD, MU, INTC) so no handful of names drives the cross-section.
> The full 500-firm sample (with them) is a **disclosed appendix**
> (`Table~\ref{tab:fullsample}`) and every conclusion holds there too (concreteness
> +8.7pp, p=0.007). All paper numbers are regenerated for both bases by
> `scripts/regenerate_paper_numbers.py` (validated to reproduce the pre-exclusion
> paper exactly) → `data/processed/analysis/paper_numbers_{full,ex5}.json`.

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
possible). Run from the repo root. Outputs go under `data/` (tracked in git —
collected data is pushed so teammates can run the analysis without API keys).

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
| 11 | `pull_controls.py` | Regression controls: prior revenue growth (momentum) + market cap at t0 → `data/processed/fundamentals/controls.parquet` |
| 12 | `run_controls_analysis.py` | Builds `analysis_table_v3.parquet` and runs the specification-ladder regressions → `data/processed/analysis/controls_regressions.csv` |

> Note: the value-chain category merge uses `analysis_table_v4.parquet` (from
> the teammate's S&P 500 classification). **Every number in the paper — ladder,
> IC, sorts, complete-case, heterogeneity, value-chain, placebo, permutation,
> leave-one-sector, coverage — is now regenerated (for both the ex-5 main base
> and the full-sample appendix) by `scripts/regenerate_paper_numbers.py`**,
> which was validated to reproduce the pre-exclusion paper exactly before the
> exclusion was applied. It supersedes the earlier ad-hoc runs. Outputs:
> `data/processed/analysis/paper_numbers_{full,ex5}.json`.
> `run_exclusion_analysis.py` (→ `exclusion_regressions.csv`,
> `exclusion_valuechain.csv`) was the initial exclusion probe and still runs.
> The hiring pipeline (6–7) has been run for snapshots `2026-06` and `2026-07`
> — rerun monthly with a new `--snapshot`.

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

## 6. Final results (July 2026 — details & tables in `reports/paper/`)

- **Seven signals tested** through the specification ladder: all four Larridin
  Tracker dimensions (adoption, proficiency, impact, maturity index) plus our
  concreteness, investment intensity, and hiring builder rate.
- **Headline (ex-5 base — the 5 semis excluded):** narrative concreteness
  survives the full specification ladder (sector FE + size + momentum):
  **+0.080, p=0.009, n=395**; passes BH-FDR within the primary family at q=0.05
  (marginal in the wider 15-test matrix). Robustness: placebo null (p=0.84),
  permutation p=0.002, significant in all 12 leave-one-sector-out runs (worst:
  consumer-disc 0.075, p=0.029), **stable when the 5 semis are added back**
  (full 500-firm sample +0.087, p=0.007 — disclosed appendix Table), LLM rerun
  93% exact / conc ρ=0.94. (Full-sample values are in `paper_numbers_full.json`.)
- All four Larridin composite dimensions: significant raw and with sector
  controls; attenuate under the size control (framed constructively in the
  paper as "measurement depth" — concreteness is the sharpened dimension).
- Returns: no positive predictability (consistent with market efficiency);
  margins: null everywhere ("growth channel, not cost channel").
- Heterogeneity (ex-5): AI-Infra category +44.9% raw / +31.6pp vs late-adopters
  with sector+size controls (p=0.005, descriptive; full sample with the 5 gives
  +34.2pp — sell-side rally is broad, carried by the remaining 25 infra names
  not NVDA-only); conc→growth significant within Physical/Late adopters
  (+0.065, p=0.025, n=214).
- Hiring: not testable against Q1 (timing); delivered as validation (ρ=0.83 vs
  POC), reliability (Jun↔Jul ρ=0.54), and movers dynamics.
- Design remains a single cross-section — associations, not causal claims.

---

## 7. Known limitations / gaps

- **Hiring samples are thin** (~half the companies have <5 usable postings,
  because Exa search depth is budget-limited to 25–60 results/company). The
  July snapshot exists (536 companies / 17,344 postings); note that Exa's
  index is **not level-stationary across months**, so cross-month comparisons
  must use within-month ranks, never raw levels. Consider normalizing by
  company size (employee count from SEC is sparse — revenue works).
- **Filings:** `concreteness` is the strongest dimension; `risk` is nearly
  degenerate (most large firms disclose AI risk similarly).
- **Coverage:** hiring ≈ all tradable companies (536); filings = 478 (needs a
  Larridin score + a US 10-K, so foreign filers / acquired firms drop out).
- 14 private/subsidiary companies have scores but no market/financial outcomes.

---

## 8. Remaining work / future extensions

1. Final presentation deck (weekly deck exists: `reports/Weekly_Update.pptx`).
2. Paper polish after team/client review (`reports/paper/main.tex`).
3. Monthly hiring snapshots going forward (scripts 6–7 with a new `--snapshot`);
   each Larridin score vintage converts the cross-section into a panel.
4. Press / news signal (free via GDELT; timestamps allow legitimate backfill).
5. Earnings-call transcripts (deferred — would enrich the filings signal).
6. Productivity outcome (employee counts extractable from cached 10-K texts).
