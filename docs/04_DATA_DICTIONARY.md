# Data Dictionary

> ⚠️ **Original scaffold design — not current reality.** The tables below (e.g. a `larridin_scores` table with `ai_adoption_score` columns) are an *assumed* schema and do NOT match Larridin's real data, which stores scores as an `aiScores` JSON object. For the real shape and the tables our pipeline produces, see [`HANDOFF.md`](../HANDOFF.md).

This document defines the canonical research tables for the AI Impact Research system. All committed sample data is synthetic. Private Larridin exports, raw vendor data, credentials, and restricted documents must stay out of git.

Timing rule: every feature used for modeling must have an observation date and `available_at`. Panel builders and backtests must only use records with `available_at` at or before the prediction date.

## `companies`

Company master table. One row per stable internal company.

| Field | Type | Required | Data source | Description | Timing and look-ahead notes |
|---|---|---:|---|---|---|
| company_id | text | Required | Internal mapping | Stable internal company identifier | Stable key for all company-level joins |
| company_name | text | Required | Public listing data or sponsor mapping | Company display or legal name | Descriptive only |
| name | text | Optional | Backward-compatible alias | Alias of `company_name` retained for older code paths | Do not treat as a separate identifier |
| ticker | text | Required | Public listing data or sponsor mapping | Normalized primary ticker at collection time | Prefer `company_id`; ticker fallback joins must emit warnings |
| cik | text | Optional | SEC/company mapping | SEC Central Index Key, preserved as zero-padded string | Supports SEC joins |
| exchange | text | Optional | Public listing data | Normalized listing exchange | Use valid-date mapping when exchange changes |
| sector | text | Optional | Public fundamentals or mapping | Sector classification | Missing sector should be reported; if used as a feature, respect classification availability date |
| industry | text | Optional | Public fundamentals or mapping | Industry classification | If used as a feature, respect classification availability date |
| country | text | Optional | Public listing data or sponsor mapping | Listing or headquarters country, depending on source contract | Source definition must be documented |
| active_from | date | Optional | Identifier mapping | First date company mapping is active | Use for point-in-time mapping when available |
| active_to | date | Optional | Identifier mapping | Last date company mapping is active | Null means current/unknown end |
| market_cap | numeric | Optional | Market/fundamental vendor | Market capitalization | Must not be used as a feature unless observation timing is known |
| source_name | text | Optional | Ingestion metadata | Source for company master record | Audit field |
| created_at | timestamptz | Required | System | Row creation timestamp | Audit field |
| updated_at | timestamptz | Required | System | Row update timestamp | Audit field |

Identifier mapping rules:

- Normalize tickers to uppercase before joining.
- Preserve CIKs as zero-padded strings.
- Detect duplicate `company_id`, duplicate ticker, duplicate CIK, and incoming rows whose `company_id` and ticker conflict with the master.
- Join on `company_id` whenever available.
- Ticker fallback joins must emit an explicit warning and report unmatched rows.
- Many-to-many joins are invalid and must raise errors.

## `company_identifiers`

Identifier history table for tickers, CIKs, exchanges, sectors, industries, and future mapping types.

| Field | Type | Required | Data source | Description | Timing and look-ahead notes |
|---|---|---:|---|---|---|
| identifier_id | text | Required | Internal mapping | Stable identifier row key | Primary key |
| company_id | text | Required | Internal mapping | Stable company key | Foreign key to `companies` |
| identifier_type | text | Required | Internal mapping | One of ticker, cik, exchange, sector, industry, other | Supports point-in-time joins |
| identifier_value | text | Required | Internal/public mapping | Identifier value | Must be matched using validity dates when available |
| valid_from | date | Optional | Source metadata | First date identifier is valid | Prevents future mappings leaking into old periods |
| valid_to | date | Optional | Source metadata | Last date identifier is valid | Null means current/unknown end |
| source_name | text | Optional | Ingestion metadata | Source of identifier mapping | Audit field |
| created_at | timestamptz | Required | System | Row creation timestamp | Audit field |

## `larridin_scores`

Canonical Larridin AI Transformation Tracker score snapshots.

| Field | Type | Required | Data source | Description | Timing and look-ahead notes |
|---|---|---:|---|---|---|
| score_id | text | Required | Internal ingestion | Stable score row key | Primary key |
| company_id | text | Required | Identifier mapping | Stable company key | Join key |
| ticker | text | Required | Larridin export | Ticker from source | Preserve source ticker |
| snapshot_date | date | Required | Larridin export | Date score snapshot was measured | Observation date |
| score_quarter | text | Required | Derived from snapshot_date | Calendar quarter label | Convenience period |
| ai_adoption_score | integer | Required | Larridin export | 1-5 AI adoption score | Feature; must use `available_at` |
| ai_fluency_score | integer | Required | Larridin export | 1-5 AI fluency score | Feature; must use `available_at` |
| ai_impact_score | integer | Required | Larridin export | 1-5 AI impact/initiatives score | Feature; must use `available_at` |
| ai_hiring_score | integer | Required | Larridin export | 1-5 AI hiring score | Feature; must use `available_at` |
| source_name | text | Optional | Ingestion metadata | Source name | Audit field |
| source_url | text | Optional | Ingestion metadata | Source URL if available | Do not expose private URLs in public outputs |
| available_at | timestamptz | Required | Larridin export or ingestion metadata | Earliest timestamp score was observable | Required for look-ahead prevention |
| raw_payload | jsonb | Optional | Larridin export | Raw source row/payload | Keep proprietary raw payloads out of git |
| created_at | timestamptz | Required | System | Row creation timestamp | Audit field |

## `market_prices`

Canonical market price observations.

| Field | Type | Required | Data source | Description | Timing and look-ahead notes |
|---|---|---:|---|---|---|
| price_id | text | Required | Internal ingestion | Stable price row key | Primary key |
| company_id | text | Required | Identifier mapping | Stable company key | Join key |
| ticker | text | Required | Market data source | Ticker from source | Preserve source ticker |
| price_date | date | Required | Market data source | Price observation date | Observation date |
| price_quarter | text | Required | Derived from price_date | Calendar quarter label | Convenience period |
| adjusted_close | numeric | Required | Market data source | Adjusted close price | Used for future outcomes, not contemporaneous model features unless intended |
| daily_return | numeric | Optional | Derived from adjusted_close | Daily percentage return within company/ticker price series | Outcome/control only after the relevant `price_date` |
| volume | numeric | Optional | Market data source | Trading volume | Feature only if available before prediction date |
| source_name | text | Optional | Ingestion metadata | Source name | Audit field |
| available_at | timestamptz | Required | Market data source | Earliest timestamp price was observable | Required for timing checks |
| raw_payload | jsonb | Optional | Market data source | Raw source row/payload | Keep large/raw data out of git |
| created_at | timestamptz | Required | System | Row creation timestamp | Audit field |

## `financial_metrics`

Canonical quarterly financial metrics.

| Field | Type | Required | Data source | Description | Timing and look-ahead notes |
|---|---|---:|---|---|---|
| metric_id | text | Required | Internal ingestion | Stable metric row key | Primary key |
| company_id | text | Required | Identifier mapping | Stable company key | Join key |
| ticker | text | Required | Financial data source | Ticker from source | Preserve source ticker |
| fiscal_quarter | text | Required | Financial data source | Fiscal quarter label | Period label, not availability date |
| fiscal_period_end | date | Required | Financial data source | Fiscal period end date | Observation period end |
| available_at | timestamptz | Required | Filing/vendor release metadata | Earliest timestamp metric was observable | Must be on or after fiscal period end unless an explicit documented warning override is used |
| revenue | numeric | Optional | Financial statements/vendor | Revenue for period | Feature/outcome only after `available_at` |
| gross_margin | numeric | Optional | Derived/vendor | Gross margin ratio | Values are normalized to ratios during ingestion |
| operating_margin | numeric | Optional | Derived/vendor | Operating margin ratio | Feature/outcome only after `available_at` |
| net_income | numeric | Optional | Financial statements/vendor | Net income for period | Feature/outcome only after `available_at` |
| employee_count | numeric | Optional | Financial statements/vendor | Employee count/headcount | Often sparse; document source definition |
| revenue_per_employee | numeric | Optional | Derived/vendor | Revenue divided by employees | Feature/outcome only after `available_at` |
| source_name | text | Optional | Ingestion metadata | Source name | Audit field |
| source_document_id | text | Optional | Source document registry | Linked source document, filing, or vendor extract ID | Preserves lineage when available |
| source_url | text | Optional | Ingestion metadata | Source URL if available | Avoid leaking private URLs |
| raw_payload | jsonb | Optional | Financial source | Raw source row/payload | Keep restricted raw data out of git |
| created_at | timestamptz | Required | System | Row creation timestamp | Audit field |

## `source_documents`

Registry for source documents used by LLM enrichment or evidence workflows.

| Field | Type | Required | Data source | Description | Timing and look-ahead notes |
|---|---|---:|---|---|---|
| source_document_id | text | Required | Internal ingestion | Stable source document key | Primary key |
| company_id | text | Optional | Identifier mapping | Stable company key | Null allowed for unmatched documents |
| ticker | text | Optional | Source document | Source ticker if present | Preserve original |
| source_type | text | Required | Ingestion metadata | sec_filing, earnings_transcript, job_posting, news, company_page, other | Drives extraction rubric |
| source_name | text | Optional | Ingestion metadata | Source name | Audit field |
| source_url | text | Optional | Ingestion metadata | Source URL | Do not expose restricted URLs |
| source_path | text | Optional | Ingestion metadata | Local/object storage path | Keep private paths out of public artifacts |
| document_date | date | Required | Source metadata | Document publication/filing/posting date | Observation date |
| collected_at | timestamptz | Required | System | Collection timestamp | Audit field |
| available_at | timestamptz | Required | Source metadata | Earliest timestamp document was observable | Required for LLM feature timing |
| content_hash | text | Optional | Ingestion metadata | Hash of document content | Reproducibility/audit |
| created_at | timestamptz | Required | System | Row creation timestamp | Audit field |

## `job_postings`

Structured job posting samples for hiring-related signals.

| Field | Type | Required | Data source | Description | Timing and look-ahead notes |
|---|---|---:|---|---|---|
| job_posting_id | text | Required | Internal ingestion | Stable job posting key | Primary key |
| company_id | text | Required | Identifier mapping | Stable company key | Join key |
| source_document_id | text | Optional | Source document registry | Linked raw/source document | Preserves evidence lineage |
| posted_date | date | Required | Job posting source | Posting observation date | Observation date |
| available_at | timestamptz | Required | Job posting source | Earliest timestamp posting was observable | Required for hiring feature timing |
| title | text | Optional | Job posting source | Job title | Can support AI hiring classification |
| location | text | Optional | Job posting source | Job location | Optional control/metadata |
| department | text | Optional | Job posting source | Department/function | Optional classification |
| seniority | text | Optional | Job posting source | Seniority level if available | Optional classification |
| ai_related | boolean | Optional | Derived classifier/manual label | Whether posting appears AI-related | Derived feature; preserve classifier version elsewhere |
| source_name | text | Optional | Ingestion metadata | Source name | Audit field |
| source_url | text | Optional | Ingestion metadata | Source URL | Avoid restricted URL leakage |
| raw_payload | jsonb | Optional | Job posting source | Raw source row/payload | Keep proprietary raw data out of git |
| created_at | timestamptz | Required | System | Row creation timestamp | Audit field |

## `llm_extractions`

Structured LLM signal enrichment outputs.

| Field | Type | Required | Data source | Description | Timing and look-ahead notes |
|---|---|---:|---|---|---|
| extraction_id | text | Required | Internal extraction run | Stable extraction key | Primary key |
| source_document_id | text | Required | Source document registry | Evidence source document key | Required for audit |
| company_id | text | Optional | Identifier mapping | Stable company key | Null allowed until matched |
| ticker | text | Optional | Source/extraction | Source ticker if present | Preserve original |
| extraction_period | text | Required | Extraction metadata | Period label associated with extraction | Observation period label |
| model_name | text | Required | LLM adapter | Model used for extraction | Reproducibility |
| prompt_version | text | Required | Prompt registry | Prompt version | Reproducibility |
| extraction_schema_version | text | Required | Schema registry | Output schema version | Reproducibility |
| extraction_json | jsonb | Required | LLM adapter | Full structured extraction | Do not treat as ground truth without review |
| evidence | jsonb | Required | LLM adapter/source text | Evidence snippets or references | Must be auditable to source document |
| confidence | numeric | Required | LLM adapter/rubric | 0-1 confidence score | Calibration must be documented |
| available_at | timestamptz | Required | Source document timing | Earliest timestamp extraction could have been produced from available evidence | Prevents future-document leakage |
| created_at | timestamptz | Required | System | Extraction creation timestamp | Audit field |

## `analytic_panel`

Company-period modeling panel. Rows must be built from point-in-time available inputs.

| Field | Type | Required | Data source | Description | Timing and look-ahead notes |
|---|---|---:|---|---|---|
| company_id | text | Required | Identifier mapping | Stable company key | Join key |
| ticker | text | Required | Identifier mapping | Ticker used for row | Point-in-time ticker preferred |
| company_name | text | Optional | Company master / Larridin scores | Company display name | Descriptive only |
| sector | text | Optional | Company master | Sector classification | Used for controls and sector-average return proxy |
| industry | text | Optional | Company master | Industry classification | Optional control/metadata |
| snapshot_date | date | Required | `larridin_scores` | Score snapshot observation date | Observation date |
| score_quarter | text | Required | Panel builder | Score/panel quarter | Period label |
| score_available_at | timestamptz | Required | `larridin_scores` | Earliest timestamp score was observable | Must be <= `prediction_date` |
| prediction_date | date | Required | Panel builder | Date predictions are formed | All feature `available_at` values must be <= this date |
| outcome_start_date | date | Optional | `market_prices` | First price date after `prediction_date` | Outcome window must start after prediction date |
| outcome_end_date | date | Optional | `market_prices` | One-quarter outcome end price date | Must be after `outcome_start_date` |
| quarter | text | Required | Panel builder | Quarter fixed-effect label | Same as `score_quarter` for MVP |
| ai_adoption_score | integer | Optional | `larridin_scores` | 1-5 AI adoption feature | Must be observable by prediction date |
| ai_fluency_score | integer | Optional | `larridin_scores` | 1-5 AI fluency feature | Must be observable by prediction date |
| ai_impact_score | integer | Optional | `larridin_scores` | 1-5 AI impact feature | Must be observable by prediction date |
| ai_hiring_score | integer | Optional | `larridin_scores` | 1-5 AI hiring feature | Must be observable by prediction date |
| composite_ai_score | numeric | Required | Derived | Simple mean of four Larridin score dimensions | Weighting must be documented if changed |
| log_market_cap | numeric | Optional | Company master / market data | Natural log of market cap if available | Use only when observation timing is known |
| prior_return_1q | numeric | Optional | `market_prices` | Return from two latest prices at or before prediction date | Feature/control only from pre-prediction prices |
| revenue_growth_qoq | numeric | Optional | `financial_metrics` | Latest available quarter-over-quarter revenue growth | Uses only financial rows with `available_at <= prediction_date` |
| operating_margin_t | numeric | Optional | `financial_metrics` | Latest available operating margin | Uses only financial rows with `available_at <= prediction_date` |
| revenue_per_employee_t | numeric | Optional | `financial_metrics` | Latest available revenue per employee | Uses only financial rows with `available_at <= prediction_date` |
| fwd_return_1q | numeric | Optional | `market_prices` | Forward one-quarter stock return | Outcome; never use as a feature for same prediction date |
| fwd_return_2q | numeric | Optional | `market_prices` | Forward two-quarter stock return | Outcome; never use as a feature for same prediction date |
| fwd_excess_return_1q | numeric | Optional | Derived from `market_prices` | Forward return minus sector-quarter average proxy | Use a benchmark column instead when available |
| future_revenue_growth_qoq | numeric | Optional | `financial_metrics` | Revenue growth between first two fiscal periods ending after prediction date | Outcome window begins after prediction date |
| future_operating_margin_delta_qoq | numeric | Optional | `financial_metrics` | Operating margin change between first two future fiscal periods | Outcome window begins after prediction date |
| future_revenue_per_employee_growth_qoq | numeric | Optional | `financial_metrics` | Revenue per employee growth between first two future fiscal periods | Requires employee counts |
| timing_warning | text | Optional | Panel builder | Semicolon-delimited timing issue notes | Non-empty rows should be reviewed |
| timing_violation | boolean | Required | Panel builder | Whether row violates timing rules | Strict mode drops these rows |
| data_snapshot_id | text | Optional | Panel builder | Data snapshot/version key | Reproducibility |
| created_at | timestamptz | Required | System | Row creation timestamp | Audit field |

## `model_runs`

Metadata for IC, regression, backtest, robustness, and report-generating runs.

| Field | Type | Required | Data source | Description | Timing and look-ahead notes |
|---|---|---:|---|---|---|
| model_run_id | text | Required | Analysis runner | Stable run key | Primary key |
| run_type | text | Required | Analysis runner | ic, regression, backtest, robustness, report, other | Output grouping |
| signal_name | text | Optional | Analysis config | Signal analyzed | Reproducibility |
| outcome_name | text | Optional | Analysis config | Outcome analyzed | Reproducibility |
| git_commit | text | Optional | Git metadata | Commit hash if available | Reproducibility |
| data_snapshot_id | text | Optional | Data/panel builder | Data snapshot/version key if available | Reproducibility |
| config_json | jsonb | Required | Analysis config | Run configuration | Required for repeatability |
| created_at | timestamptz | Required | System | Run creation timestamp | Audit field |

## `ic_results`

Information coefficient result rows.

| Field | Type | Required | Data source | Description | Timing and look-ahead notes |
|---|---|---:|---|---|---|
| ic_result_id | text | Required | IC analysis | Stable result key | Primary key |
| model_run_id | text | Required | `model_runs` | Parent run key | Reproducibility |
| signal_name | text | Required | Analysis config | Signal tested | Audit field |
| outcome_name | text | Required | Analysis config | Outcome tested | Audit field |
| period | text | Optional | IC analysis | Result period | Period label |
| ic_value | numeric | Optional | IC analysis | Spearman/Pearson IC value | Method in config_json |
| p_value | numeric | Optional | IC analysis | Statistical p-value | Interpret carefully with multiple tests |
| n_obs | integer | Optional | IC analysis | Number of observations | Coverage field |
| git_commit | text | Optional | Git metadata | Commit hash if available | Reproducibility |
| data_snapshot_id | text | Optional | Data/panel builder | Data snapshot/version key if available | Reproducibility |
| config_json | jsonb | Optional | Analysis config | Result-specific config | Reproducibility |
| created_at | timestamptz | Required | System | Result creation timestamp | Audit field |

## `regression_results`

Regression coefficient result rows.

| Field | Type | Required | Data source | Description | Timing and look-ahead notes |
|---|---|---:|---|---|---|
| regression_result_id | text | Required | Regression analysis | Stable result key | Primary key |
| model_run_id | text | Required | `model_runs` | Parent run key | Reproducibility |
| signal_name | text | Required | Analysis config | Primary signal tested | Audit field |
| outcome_name | text | Required | Analysis config | Outcome tested | Audit field |
| term | text | Required | Regression model | Coefficient term name | Includes controls/fixed effects when exported |
| coefficient | numeric | Optional | Regression model | Estimated coefficient | Research artifact |
| std_error | numeric | Optional | Regression model | Standard error | Method must be in config_json |
| t_value | numeric | Optional | Regression model | t-statistic | Research artifact |
| p_value | numeric | Optional | Regression model | Statistical p-value | Interpret carefully |
| n_obs | integer | Optional | Regression model | Number of observations | Coverage field |
| git_commit | text | Optional | Git metadata | Commit hash if available | Reproducibility |
| data_snapshot_id | text | Optional | Data/panel builder | Data snapshot/version key if available | Reproducibility |
| config_json | jsonb | Optional | Analysis config | Result-specific config | Reproducibility |
| created_at | timestamptz | Required | System | Result creation timestamp | Audit field |

## `backtest_results`

Quintile and long-short backtest result rows.

| Field | Type | Required | Data source | Description | Timing and look-ahead notes |
|---|---|---:|---|---|---|
| backtest_result_id | text | Required | Backtest runner | Stable result key | Primary key |
| model_run_id | text | Required | `model_runs` | Parent run key | Reproducibility |
| metric_name | text | Required | Backtest runner | Metric name | Example: mean_return, long_short_return |
| metric_value | numeric | Optional | Backtest runner | Metric value | Hypothetical research result |
| period | text | Optional | Backtest runner | Result period | Rebalance/holding period label |
| quantile | integer | Optional | Backtest runner | Signal quantile | Required for quintile rows |
| signal_name | text | Optional | Analysis config | Signal used | Reproducibility |
| outcome_name | text | Optional | Analysis config | Return/outcome used | Reproducibility |
| metric_json | jsonb | Optional | Backtest runner | Additional metrics | Reproducibility |
| git_commit | text | Optional | Git metadata | Commit hash if available | Reproducibility |
| data_snapshot_id | text | Optional | Data/panel builder | Data snapshot/version key if available | Reproducibility |
| config_json | jsonb | Optional | Analysis config | Result-specific config | Reproducibility |
| created_at | timestamptz | Required | System | Result creation timestamp | Audit field |
