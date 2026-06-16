-- ============================================================================
-- ⚠️ LOCAL / REFERENCE SCHEMA ONLY — NOT the source of truth.
--
-- Larridin's real Supabase schema is authoritative. Do NOT run this against the
-- shared Supabase database. When access lands, inspect their schema first and
-- reconcile this file to it (column names, types, point-in-time / snapshot
-- handling).
--
-- Known issues to verify against real data:
--   * larridin_scores assumes INTEGER scores CHECK (1..5) and
--     UNIQUE(company_id, snapshot_date, source_name). Real scores may be
--     non-integer, revised-in-place, or keyed differently — verify before relying.
--   * analytic_panel columns here (revenue_growth, operating_margin_delta,
--     revenue_per_employee_growth, headcount_growth, ai_composite_score,
--     panel_date) do NOT match what panel_builder.py / docs/04_DATA_DICTIONARY.md
--     actually produce (future_*_qoq, composite_ai_score,
--     snapshot_date/prediction_date). Known naming drift — unify against real
--     data, not now.
-- ============================================================================

CREATE TABLE IF NOT EXISTS companies (
    company_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    name TEXT NOT NULL,
    company_name TEXT,
    sector TEXT,
    industry TEXT,
    cik TEXT,
    exchange TEXT,
    country TEXT,
    active_from DATE,
    active_to DATE,
    market_cap NUMERIC,
    source_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS company_identifiers (
    identifier_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    identifier_type TEXT NOT NULL CHECK (
        identifier_type IN ('ticker', 'cik', 'exchange', 'sector', 'industry', 'other')
    ),
    identifier_value TEXT NOT NULL,
    valid_from DATE,
    valid_to DATE,
    source_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (company_id, identifier_type, identifier_value, valid_from)
);

CREATE TABLE IF NOT EXISTS larridin_scores (
    score_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    ticker TEXT NOT NULL,
    snapshot_date DATE NOT NULL,
    score_quarter TEXT NOT NULL,
    ai_adoption_score INTEGER NOT NULL CHECK (ai_adoption_score BETWEEN 1 AND 5),
    ai_fluency_score INTEGER NOT NULL CHECK (ai_fluency_score BETWEEN 1 AND 5),
    ai_impact_score INTEGER NOT NULL CHECK (ai_impact_score BETWEEN 1 AND 5),
    ai_hiring_score INTEGER NOT NULL CHECK (ai_hiring_score BETWEEN 1 AND 5),
    source_name TEXT,
    source_url TEXT,
    available_at TIMESTAMPTZ NOT NULL,
    raw_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (company_id, snapshot_date, source_name)
);

CREATE TABLE IF NOT EXISTS market_prices (
    price_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    ticker TEXT NOT NULL,
    price_date DATE NOT NULL,
    price_quarter TEXT NOT NULL,
    adjusted_close NUMERIC NOT NULL,
    daily_return NUMERIC,
    volume NUMERIC,
    source_name TEXT,
    available_at TIMESTAMPTZ NOT NULL,
    raw_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (company_id, price_date, source_name)
);

CREATE TABLE IF NOT EXISTS financial_metrics (
    metric_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    ticker TEXT NOT NULL,
    fiscal_quarter TEXT NOT NULL,
    fiscal_period_end DATE NOT NULL,
    revenue NUMERIC,
    gross_margin NUMERIC,
    operating_margin NUMERIC,
    net_income NUMERIC,
    employee_count NUMERIC,
    revenue_per_employee NUMERIC,
    source_name TEXT,
    source_document_id TEXT,
    source_url TEXT,
    available_at TIMESTAMPTZ NOT NULL,
    raw_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (company_id, fiscal_quarter, source_name)
);

CREATE TABLE IF NOT EXISTS source_documents (
    source_document_id TEXT PRIMARY KEY,
    company_id TEXT REFERENCES companies(company_id),
    ticker TEXT,
    source_type TEXT NOT NULL CHECK (
        source_type IN ('sec_filing', 'earnings_transcript', 'job_posting', 'news', 'company_page', 'other')
    ),
    source_name TEXT,
    source_url TEXT,
    source_path TEXT,
    document_date DATE NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    content_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS job_postings (
    job_posting_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    source_document_id TEXT REFERENCES source_documents(source_document_id),
    posted_date DATE NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    title TEXT,
    location TEXT,
    department TEXT,
    seniority TEXT,
    ai_related BOOLEAN,
    source_name TEXT,
    source_url TEXT,
    raw_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS llm_extractions (
    extraction_id TEXT PRIMARY KEY,
    source_document_id TEXT NOT NULL REFERENCES source_documents(source_document_id),
    company_id TEXT REFERENCES companies(company_id),
    ticker TEXT,
    extraction_period TEXT NOT NULL,
    model_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    extraction_schema_version TEXT NOT NULL,
    extraction_json JSONB NOT NULL,
    evidence JSONB NOT NULL,
    confidence NUMERIC NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    available_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analytic_panel (
    panel_row_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    ticker TEXT NOT NULL,
    panel_date DATE NOT NULL,
    score_quarter TEXT NOT NULL,
    prediction_date DATE NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    ai_adoption_score INTEGER CHECK (ai_adoption_score BETWEEN 1 AND 5),
    ai_fluency_score INTEGER CHECK (ai_fluency_score BETWEEN 1 AND 5),
    ai_impact_score INTEGER CHECK (ai_impact_score BETWEEN 1 AND 5),
    ai_hiring_score INTEGER CHECK (ai_hiring_score BETWEEN 1 AND 5),
    ai_composite_score NUMERIC,
    fwd_return_1q NUMERIC,
    fwd_return_2q NUMERIC,
    revenue_growth NUMERIC,
    operating_margin_delta NUMERIC,
    revenue_per_employee_growth NUMERIC,
    headcount_growth NUMERIC,
    data_snapshot_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (company_id, panel_date, data_snapshot_id)
);

CREATE TABLE IF NOT EXISTS model_runs (
    model_run_id TEXT PRIMARY KEY,
    run_type TEXT NOT NULL,
    signal_name TEXT,
    outcome_name TEXT,
    git_commit TEXT,
    data_snapshot_id TEXT,
    config_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ic_results (
    ic_result_id TEXT PRIMARY KEY,
    model_run_id TEXT NOT NULL REFERENCES model_runs(model_run_id),
    signal_name TEXT NOT NULL,
    outcome_name TEXT NOT NULL,
    period TEXT,
    ic_value NUMERIC,
    p_value NUMERIC,
    n_obs INTEGER,
    git_commit TEXT,
    data_snapshot_id TEXT,
    config_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS regression_results (
    regression_result_id TEXT PRIMARY KEY,
    model_run_id TEXT NOT NULL REFERENCES model_runs(model_run_id),
    signal_name TEXT NOT NULL,
    outcome_name TEXT NOT NULL,
    term TEXT NOT NULL,
    coefficient NUMERIC,
    std_error NUMERIC,
    t_value NUMERIC,
    p_value NUMERIC,
    n_obs INTEGER,
    git_commit TEXT,
    data_snapshot_id TEXT,
    config_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS backtest_results (
    backtest_result_id TEXT PRIMARY KEY,
    model_run_id TEXT NOT NULL REFERENCES model_runs(model_run_id),
    metric_name TEXT NOT NULL,
    metric_value NUMERIC,
    period TEXT,
    quantile INTEGER,
    signal_name TEXT,
    outcome_name TEXT,
    metric_json JSONB,
    git_commit TEXT,
    data_snapshot_id TEXT,
    config_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
