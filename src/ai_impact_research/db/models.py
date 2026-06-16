from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CANONICAL_TABLES: tuple[str, ...] = (
    "companies",
    "company_identifiers",
    "larridin_scores",
    "market_prices",
    "financial_metrics",
    "source_documents",
    "job_postings",
    "llm_extractions",
    "analytic_panel",
    "model_runs",
    "ic_results",
    "regression_results",
    "backtest_results",
)

MODEL_REQUIRED_COLUMNS: dict[str, set[str]] = {
    "companies": {"company_id", "ticker", "name"},
    "company_identifiers": {"identifier_id", "company_id", "identifier_type", "identifier_value"},
    "larridin_scores": {
        "ticker",
        "company_name",
        "snapshot_date",
        "ai_adoption_score",
        "ai_fluency_score",
        "ai_impact_score",
        "ai_hiring_score",
    },
    "market_prices": {"ticker", "price_date", "adjusted_close"},
    "financial_metrics": {
        "ticker",
        "fiscal_quarter",
        "fiscal_period_end",
        "revenue",
        "operating_margin",
    },
    "source_documents": {"source_document_id", "source_type", "document_date", "available_at"},
    "job_postings": {"job_posting_id", "company_id", "posted_date", "available_at"},
    "llm_extractions": {
        "extraction_id",
        "source_document_id",
        "model_name",
        "prompt_version",
        "extraction_schema_version",
        "evidence",
        "confidence",
        "available_at",
    },
    "analytic_panel": {"panel_row_id", "company_id", "panel_date", "available_at"},
    "model_runs": {"model_run_id", "run_type", "config_json", "created_at"},
    "ic_results": {"ic_result_id", "model_run_id", "signal_name", "outcome_name", "ic_value"},
    "regression_results": {
        "regression_result_id",
        "model_run_id",
        "signal_name",
        "outcome_name",
        "coefficient",
    },
    "backtest_results": {"backtest_result_id", "model_run_id", "metric_name", "metric_value"},
}


class RecordModel(BaseModel):
    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)


class CompanyRecord(RecordModel):
    company_id: str
    ticker: str
    name: str
    company_name: str | None = None
    sector: str | None = None
    industry: str | None = None
    cik: str | None = None
    exchange: str | None = None
    country: str | None = None
    active_from: date | None = None
    active_to: date | None = None
    market_cap: float | None = None

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.upper().strip()


class CompanyIdentifierRecord(RecordModel):
    identifier_id: str
    company_id: str
    identifier_type: Literal["ticker", "cik", "exchange", "sector", "industry", "other"]
    identifier_value: str
    valid_from: date | None = None
    valid_to: date | None = None
    source_name: str | None = None


class LarridinScoreRecord(RecordModel):
    score_id: str
    company_id: str
    ticker: str
    snapshot_date: date
    score_quarter: str
    ai_adoption_score: int = Field(..., ge=1, le=5)
    ai_fluency_score: int = Field(..., ge=1, le=5)
    ai_impact_score: int = Field(..., ge=1, le=5)
    ai_hiring_score: int = Field(..., ge=1, le=5)
    source_name: str | None = None
    source_url: str | None = None
    available_at: datetime

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.upper().strip()


class MarketPriceRecord(RecordModel):
    price_id: str
    company_id: str
    ticker: str
    price_date: date
    price_quarter: str
    adjusted_close: float
    daily_return: float | None = None
    volume: float | None = None
    source_name: str | None = None
    available_at: datetime


class FinancialMetricRecord(RecordModel):
    metric_id: str
    company_id: str
    ticker: str
    fiscal_quarter: str
    fiscal_period_end: date
    revenue: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    net_income: float | None = None
    employee_count: float | None = None
    source_name: str | None = None
    source_document_id: str | None = None
    available_at: datetime


class SourceDocumentRecord(RecordModel):
    source_document_id: str
    company_id: str | None = None
    ticker: str | None = None
    source_type: Literal["sec_filing", "earnings_transcript", "job_posting", "news", "company_page", "other"]
    source_name: str | None = None
    source_url: str | None = None
    source_path: str | None = None
    document_date: date
    collected_at: datetime
    available_at: datetime
    content_hash: str | None = None


class JobPostingRecord(RecordModel):
    job_posting_id: str
    company_id: str
    source_document_id: str | None = None
    posted_date: date
    available_at: datetime
    title: str | None = None
    location: str | None = None
    source_name: str | None = None


class LLMExtractionRecord(RecordModel):
    extraction_id: str
    source_document_id: str
    model_name: str
    prompt_version: str
    extraction_schema_version: str
    evidence: list[dict[str, Any]]
    confidence: float = Field(..., ge=0, le=1)
    available_at: datetime
    created_at: datetime


class AnalyticPanelRecord(RecordModel):
    panel_row_id: str
    company_id: str
    ticker: str
    panel_date: date
    score_quarter: str
    prediction_date: date
    available_at: datetime
    ai_adoption_score: int | None = Field(None, ge=1, le=5)
    ai_fluency_score: int | None = Field(None, ge=1, le=5)
    ai_impact_score: int | None = Field(None, ge=1, le=5)
    ai_hiring_score: int | None = Field(None, ge=1, le=5)
    data_snapshot_id: str | None = None


class ModelRunRecord(RecordModel):
    model_run_id: str
    run_type: str
    signal_name: str | None = None
    outcome_name: str | None = None
    git_commit: str | None = None
    data_snapshot_id: str | None = None
    config_json: dict[str, Any]
    created_at: datetime


class ICResultRecord(RecordModel):
    ic_result_id: str
    model_run_id: str
    signal_name: str
    outcome_name: str
    ic_value: float | None = None
    git_commit: str | None = None
    data_snapshot_id: str | None = None
    config_json: dict[str, Any] | None = None
    created_at: datetime


class RegressionResultRecord(RecordModel):
    regression_result_id: str
    model_run_id: str
    signal_name: str
    outcome_name: str
    term: str
    coefficient: float | None = None
    git_commit: str | None = None
    data_snapshot_id: str | None = None
    config_json: dict[str, Any] | None = None
    created_at: datetime


class BacktestResultRecord(RecordModel):
    backtest_result_id: str
    model_run_id: str
    metric_name: str
    metric_value: float | None = None
    git_commit: str | None = None
    data_snapshot_id: str | None = None
    config_json: dict[str, Any] | None = None
    created_at: datetime


def validate_required_columns(table_name: str, columns: list[str] | set[str]) -> None:
    if table_name not in MODEL_REQUIRED_COLUMNS:
        raise ValueError(f"Unknown table for required column validation: {table_name}")
    missing = MODEL_REQUIRED_COLUMNS[table_name] - set(columns)
    if missing:
        raise ValueError(f"{table_name} is missing required columns: {sorted(missing)}")
