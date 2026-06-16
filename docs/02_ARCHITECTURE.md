# Architecture

> ⚠️ **Original scaffold design — not current reality.** This describes the project as first planned. The actual Larridin data and the pipeline we built differ in important ways. See [`HANDOFF.md`](../HANDOFF.md) for the current state.

## Target architecture

```text
External Sources
  ├── Larridin API / CSV export
  ├── SEC EDGAR / XBRL
  ├── Market price data
  ├── Earnings transcripts
  ├── Job postings
  └── News / web sources

        ↓ ingestion

Raw Layer
  ├── raw JSON / CSV / HTML / text
  └── source metadata and hashes

        ↓ normalization

Canonical Layer
  ├── companies
  ├── identifiers
  ├── larridin_scores
  ├── financial_metrics
  ├── market_prices
  ├── source_documents
  └── llm_extractions

        ↓ feature engineering

Analytical Panel
  ├── company_id
  ├── score_quarter
  ├── AI signals at t
  ├── controls at t
  ├── outcomes at t+1 / t+2 / t+4
  └── available_at timestamps

        ↓ analysis

Research Outputs
  ├── IC
  ├── regressions
  ├── quintile backtests
  ├── robustness checks
  └── report-ready tables

        ↓ product

Dashboard + ticker report generator
```

## Design principles

1. Separate ingestion, transformation, analysis, and presentation.
2. Keep Streamlit thin; it should visualize outputs, not own core logic.
3. Store raw data and normalized data separately.
4. Version prompts and LLM outputs.
5. Treat time availability as a first-class field.
