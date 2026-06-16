# Data Sources

> ⚠️ **Original scaffold design — not current reality.** This describes the project as first planned (CSV/API stubs). The real sources are Larridin's Supabase (REST), Exa, SEC EDGAR, and yfinance. See [`HANDOFF.md`](../HANDOFF.md) for the current state.

## Larridin scores

Purpose: Core AI adoption signals.

MVP ingestion mode: CSV export only. Use `scripts/ingest_larridin.py`; do not call private APIs in tests or local smoke workflows.

Expected CSV fields:

- `company_id` or `ticker`
- `company_name`, if available
- `snapshot_date`
- `available_at`
- `ai_adoption_score`
- `ai_fluency_score`
- `ai_impact_score`
- `ai_hiring_score`
- `source_name`
- `source_url` or `source_reference`, if available

Ingestion rules:

- Tickers are normalized to uppercase.
- Score values must be whole numbers from 1 to 5.
- `snapshot_date` and `available_at` must parse as dates.
- Extra CSV columns are preserved in `metadata_json` in the normalized output.
- `available_at` is required. If a source export lacks it, the CLI allows `--available-at YYYY-MM-DD`; this is an explicit timing assumption and must be documented in downstream analysis.
- Normalized outputs should be written to `data/processed/larridin_scores_normalized.csv` or `.parquet`.

Future API mode:

- `LarridinAPIClient` is a stub until sponsor endpoint shape, authentication, pagination, and rate limits are confirmed.
- Do not hardcode private endpoint assumptions.
- Do not add network calls to tests.

## Financial metrics

Purpose: Operational outcomes and controls.

MVP ingestion mode: CSV export only. Use `scripts/ingest_financials.py`; tests and local smoke workflows must remain offline.

Expected CSV fields:

- `company_id` or `ticker`
- `fiscal_quarter`
- `fiscal_period_end`
- `available_at`
- `revenue`
- `gross_margin`, if available
- `operating_margin`, if available
- `net_income`, if available
- `employee_count`, if available
- `source_name`, if available
- `source_document_id`, if available

Ingestion rules:

- Tickers are normalized to uppercase.
- `fiscal_period_end` and `available_at` must parse as dates.
- `available_at` must be on or after `fiscal_period_end` by default. The CLI flag `--allow-early-available-at` emits a warning and should only be used for synthetic data or explicitly documented timing assumptions.
- `revenue` must be numeric.
- Margin fields are normalized as ratios: values between 0 and 1 are preserved, and percentage-style values between 1 and 100 are divided by 100.
- `employee_count` must be positive when present.
- Normalized outputs should be written to `data/processed/financial_metrics_normalized.csv` or `.parquet`.

Future API mode:

- `SECCompanyFactsAdapter` and `FinancialDataAPIClient` are stubs for future SEC EDGAR or vendor integration.
- Do not add network calls until source contracts, rate limits, and safe mocks are defined.

## Market data

Purpose: Forward return outcomes and hypothetical portfolio backtest.

MVP ingestion mode: CSV export only. Use `scripts/ingest_market_data.py`; tests and local smoke workflows must remain offline.

Expected CSV fields:

- `company_id` or `ticker`
- `date`
- `adjusted_close`
- `volume`, if available
- `source_name`, if available

Ingestion rules:

- Tickers are normalized to uppercase.
- `date` is parsed and normalized to `price_date`.
- Rows are sorted by company/ticker and date.
- `adjusted_close` must be numeric and greater than 0.
- `daily_return` is computed from adjusted closes within each company/ticker series when enough data exists.
- `available_at` defaults to the price date for CSV market prices unless the source provides a stricter timestamp.
- Normalized outputs should be written to `data/processed/market_prices_normalized.csv` or `.parquet`.

Future API mode:

- `MarketDataAPIClient` is a stub for future market data vendor integration.
- Do not add network calls until source contracts, rate limits, and safe mocks are defined.

## Unstructured sources

Purpose: LLM enrichment.

Sources:

- 10-K / 10-Q filings
- earnings call transcripts
- job postings
- news articles
- company AI initiative pages

## Job postings

Purpose: AI hiring signal research and future LLM enrichment from public recruiting text.

MVP ingestion mode: CSV export only. Use `scripts/sample_job_postings.py`; do not scrape websites or call LLM APIs in this phase.

Expected CSV fields:

- `job_posting_id`
- `company_id` or `ticker`
- `title`
- `department`, if available
- `location`, if available
- `description`, if available
- `posting_date`, if available
- `collected_at`
- `source_url`, if available
- `source_name`
- `is_active`, if available

Normalization rules:

- Tickers are normalized to uppercase.
- Titles and text fields are whitespace-normalized.
- `posting_date` is optional because many company career pages omit it.
- `collected_at` is required and must preserve when the posting was observed.
- A SHA-256 `raw_hash` is computed from normalized title, department, location, description, and source URL to support duplicate detection.
- Likely duplicates are flagged within the same company or ticker; they are not dropped automatically.

Deterministic AI keyword classifier terms:

- artificial intelligence
- machine learning
- generative AI
- LLM
- NLP
- computer vision
- data scientist
- ML engineer
- prompt engineer
- AI product
- AI platform
- automation engineer

Sampling buckets:

- `ai_keyword_matched`
- `technical_non_ai`
- `non_technical`
- `leadership_strategy`

Sampling outputs preserve `sample_weight`, `sampling_bucket`, `random_seed`, and `sampled_at`. Sampling must never request more rows from a bucket than are available.

## Data quality notes

- Job posting pages are not standardized.
- Large companies may have tens of thousands of openings; use defensible sampling.
- Companies disclose AI adoption differently, which creates disclosure bias.
- Always preserve `source_name`, `source_url`, `source_path`, `snapshot_date`, and `available_at`.
