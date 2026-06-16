# AGENTS.md

These instructions apply to the entire repository.

## 1. Project Purpose

This repository supports the Larridin x CMU AI Capstone project: a reproducible AI impact research system that tests whether AI adoption signals predict future public-company performance.

The system combines Larridin AI Transformation Tracker scores with public financial, market, and company data, then evaluates whether those signals predict outcomes such as forward stock returns, revenue growth, margin expansion, revenue per employee, and hiring or headcount indicators when available.

Treat this as a research-grade data and analytics pipeline, not a dashboard-only demo. Work should support reproducibility, auditability, and clear separation between raw inputs, derived features, analysis outputs, and user-facing presentation.

## 2. Repository Expectations

- Prefer small, reviewable changes over broad rewrites.
- Read the current code, tests, docs, and schemas before changing behavior.
- Keep application logic in `src/ai_impact_research/`, runnable entry points in `scripts/`, documentation in `docs/`, infrastructure definitions in `infra/`, and tests in `tests/`.
- Use the Makefile for common commands when available.
- Preserve the existing Python package structure unless a phase explicitly calls for changing it.
- Keep notebooks, ad hoc experiments, and one-off scratch files out of core workflows unless they are clearly documented and not required for reproducibility.
- Update documentation and tests with meaningful behavior changes.
- Do not modify unrelated files or refactor unrelated modules while completing a phase.
- Do not invent real results, real company findings, benchmark numbers, or data coverage claims.
- Label all research outputs as exploratory or hypothetical unless they come from verified data and documented methodology.

## 3. Python Style Guide

- Use Python 3.11 or newer.
- Use pandas, numpy, and pyarrow for tabular data workflows.
- Use Pydantic for canonical schemas, validation, and structured LLM extraction outputs.
- Use DuckDB for local analytical workflows and Postgres-compatible SQL for shared storage schemas.
- Use statsmodels, scipy, and scikit-learn for research analysis.
- Use Streamlit and Plotly for dashboard work.
- Prefer typed functions with clear inputs and outputs.
- Keep functions small, deterministic, and testable.
- Separate parsing, validation, transformation, persistence, analysis, and presentation logic.
- Avoid hard-coded paths, credentials, dates, tickers, or magic constants. Put configuration in `configs/`, environment variables, or explicit function parameters.
- Use vectorized pandas operations where they improve clarity, but do not sacrifice correctness or auditability.
- Use ruff for linting and formatting expectations.

## 4. Testing Expectations

- Use pytest for all tests.
- Every significant module must have tests.
- Add or update tests when changing ingestion, schema validation, panel construction, analysis, backtesting, LLM extraction, report generation, or dashboard data adapters.
- Include edge cases for missing values, duplicate records, invalid scores, timestamp ordering, and empty inputs when relevant.
- Prefer deterministic sample data and fixtures.
- Tests must not require real API keys, proprietary sponsor data, or live network calls.
- Smoke tests should run against clearly marked synthetic data under `data/samples/`.
- For each phase, run the most relevant checks before committing. Prefer `make test` and `make lint` when available.

## 5. Data Governance Rules

- Do not commit proprietary raw data, sponsor-private exports, API responses with restricted terms, PII, credentials, or sensitive company-specific materials.
- Keep raw data in ignored locations such as `data/raw/` or managed external storage.
- Sample data committed to the repo must be clearly marked synthetic.
- Preserve source metadata for derived datasets, including source name, source document ID or path, snapshot date, and creation time where applicable.
- Every derived dataset should record enough lineage to recreate or audit it.
- Every canonical table must be documented in `docs/04_DATA_DICTIONARY.md`.
- Do not overwrite raw inputs in place. Write normalized or derived data to separate paths or tables.
- Treat backtests and analysis outputs as research artifacts, not investment advice.

## 6. Secrets Policy

- Never commit real API keys, tokens, passwords, database credentials, private SSH keys, OAuth secrets, or signed URLs.
- Store local secrets in `.env` or another ignored file.
- Provide required variable names and safe placeholder values in `.env.example`.
- Scrub secrets from logs, test fixtures, screenshots, and generated reports.
- If a secret is accidentally committed, stop work and alert the user. Do not try to hide the issue with a normal cleanup commit.

## 7. Look-Ahead Bias Prevention Rules

- Every model feature must have an observation date or `available_at` timestamp.
- Panel construction must only use features observable at or before the prediction date.
- Financial metrics must use the date they became available, not only the fiscal period end date.
- Larridin scores must use the relevant score snapshot date and `available_at` timestamp.
- Market outcomes must be computed from future periods relative to the signal date, never used as contemporaneous features.
- Backtests must define rebalance dates, holding periods, signal availability, and universe membership rules before calculating returns.
- Do not use restated, future-corrected, or survivorship-biased data unless the limitation is explicitly documented.
- Tests for panel builders and backtests should include timestamp-ordering checks.

## 8. LLM Extraction Rules

- LLM-derived signals must preserve source evidence, prompt version, model name, source document ID, schema version, confidence, and `created_at`.
- Store structured extraction results with Pydantic schemas.
- Keep prompts versioned under the repository when they are part of a reproducible workflow.
- Do not treat LLM output as ground truth without evidence and validation.
- Do not fabricate citations, excerpts, source documents, scores, or confidence values.
- Preserve enough source text or source references to audit why an extraction was made.
- Keep extraction workflows deterministic where feasible by documenting model settings.
- Clearly separate sponsor-provided Larridin scores from experimental LLM-enriched signals.

## 9. Dashboard Rules

- The Streamlit dashboard should present research workflows clearly: coverage, signal distributions, IC analysis, regression summaries, backtest outputs, and ticker-level reports.
- Keep heavy data preparation and analysis logic outside Streamlit pages. Put reusable logic in package modules.
- Dashboard views should consume validated data or prepared analytical panels.
- Label synthetic sample data and hypothetical backtests visibly.
- Do not expose secrets, private raw data, or proprietary source details in dashboard output.
- Use Plotly for interactive charts.
- Avoid claiming causality or investment performance from exploratory correlations.

## 10. Documentation Rules

- Keep README quick-start instructions current.
- Keep `docs/04_DATA_DICTIONARY.md` synchronized with every canonical table and field.
- Document data sources, assumptions, known limitations, and reproducibility steps.
- Update methodology docs when changing IC analysis, regressions, portfolio construction, robustness checks, or report generation.
- Document prompt versions and schema versions for LLM workflows.
- Write concise documentation that a new teammate can run and audit.
- Prefer exact commands, file paths, and acceptance criteria over vague prose.

## 11. Definition of Done for Every Codex Task

Every Codex task is done only when all applicable items are satisfied:

- The requested change is implemented with the smallest practical scope.
- No application code is changed when the task is documentation-only.
- Relevant tests, lint checks, or smoke checks have been run, or any skipped checks are explained.
- New or changed significant modules have tests.
- Canonical schema changes are reflected in `infra/db_schema.sql` and `docs/04_DATA_DICTIONARY.md`.
- Every new model feature includes an observation date or `available_at` timestamp.
- Look-ahead bias risks have been reviewed for panel and backtest changes.
- LLM-derived signal changes preserve source evidence, prompt version, model name, source document ID, schema version, confidence, and `created_at`.
- No real secrets, credentials, proprietary raw data, or unmarked synthetic data are committed.
- Documentation is updated for changed behavior, assumptions, commands, and data contracts.
- Git status is reviewed before committing so unrelated user changes are not staged.
- The final response summarizes what changed, validation performed, and remaining follow-up tasks.
