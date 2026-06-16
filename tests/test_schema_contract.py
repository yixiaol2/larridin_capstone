from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_impact_research.db.models import (
    CANONICAL_TABLES,
    MODEL_REQUIRED_COLUMNS,
    AnalyticPanelRecord,
    CompanyRecord,
    LarridinScoreRecord,
    ModelRunRecord,
    SourceDocumentRecord,
    validate_required_columns,
)

SCHEMA_SQL = Path("infra/db_schema.sql").read_text(encoding="utf-8")


def _table_body(table_name: str) -> str:
    match = re.search(
        rf"CREATE TABLE IF NOT EXISTS {table_name}\s*\((.*?)\n\);",
        SCHEMA_SQL,
        flags=re.DOTALL | re.IGNORECASE,
    )
    assert match is not None, f"Missing CREATE TABLE for {table_name}"
    return match.group(1)


def test_all_canonical_tables_are_defined_in_contract_and_sql() -> None:
    expected = [
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
    ]

    assert list(CANONICAL_TABLES) == expected
    for table in expected:
        body = _table_body(table)
        assert "PRIMARY KEY" in body


def test_feature_tables_include_observation_date_and_available_at() -> None:
    for table, observation_col in {
        "larridin_scores": "snapshot_date",
        "market_prices": "price_date",
        "financial_metrics": "fiscal_period_end",
        "source_documents": "document_date",
        "job_postings": "posted_date",
        "llm_extractions": "extraction_period",
        "analytic_panel": "panel_date",
    }.items():
        body = _table_body(table)
        assert observation_col in body
        assert "available_at" in body


def test_identifier_and_model_output_contract_fields_are_in_sql() -> None:
    companies = _table_body("companies")
    for field in ["company_name", "country", "active_from", "active_to"]:
        assert field in companies

    identifiers = _table_body("company_identifiers")
    for field in ["company_id", "identifier_type", "identifier_value", "valid_from", "valid_to"]:
        assert field in identifiers

    llm = _table_body("llm_extractions")
    for field in [
        "source_document_id",
        "model_name",
        "prompt_version",
        "extraction_schema_version",
        "evidence",
        "confidence",
        "created_at",
    ]:
        assert field in llm

    for table in ["model_runs", "ic_results", "regression_results", "backtest_results"]:
        body = _table_body(table)
        for field in ["model_run_id", "git_commit", "data_snapshot_id", "config_json", "created_at"]:
            assert field in body


def test_market_and_financial_ingestion_fields_are_in_sql() -> None:
    market = _table_body("market_prices")
    for field in ["adjusted_close", "daily_return", "volume", "available_at"]:
        assert field in market

    financial = _table_body("financial_metrics")
    for field in [
        "revenue",
        "gross_margin",
        "operating_margin",
        "net_income",
        "employee_count",
        "source_document_id",
        "available_at",
    ]:
        assert field in financial


def test_pydantic_models_parse_dates_and_validate_scores() -> None:
    company = CompanyRecord(company_id="C001", ticker="msft", name="Microsoft")
    assert company.ticker == "MSFT"

    score = LarridinScoreRecord(
        score_id="score_1",
        company_id="C001",
        ticker="msft",
        snapshot_date="2025-03-31",
        score_quarter="2025Q1",
        ai_adoption_score=5,
        ai_fluency_score=4,
        ai_impact_score=3,
        ai_hiring_score=2,
        available_at="2025-04-02T00:00:00Z",
    )
    assert score.snapshot_date == date(2025, 3, 31)
    assert isinstance(score.available_at, datetime)

    with pytest.raises(ValidationError):
        LarridinScoreRecord(
            score_id="score_bad",
            company_id="C001",
            ticker="MSFT",
            snapshot_date="2025-03-31",
            score_quarter="2025Q1",
            ai_adoption_score=6,
            ai_fluency_score=4,
            ai_impact_score=3,
            ai_hiring_score=2,
            available_at="2025-04-02T00:00:00Z",
        )


def test_source_document_model_preserves_timing() -> None:
    document = SourceDocumentRecord(
        source_document_id="doc_1",
        company_id="C001",
        source_type="sec_filing",
        document_date="2025-03-31",
        collected_at="2025-04-02T00:00:00Z",
        available_at="2025-04-01T00:00:00Z",
    )

    assert document.document_date == date(2025, 3, 31)
    assert document.available_at <= document.collected_at


def test_panel_and_model_run_models_preserve_provenance() -> None:
    panel_row = AnalyticPanelRecord(
        panel_row_id="panel_1",
        company_id="C001",
        ticker="MSFT",
        panel_date="2025-03-31",
        score_quarter="2025Q1",
        prediction_date="2025-04-03",
        available_at="2025-04-02T00:00:00Z",
        ai_adoption_score=5,
        data_snapshot_id="snapshot_1",
    )
    model_run = ModelRunRecord(
        model_run_id="run_1",
        run_type="ic",
        git_commit="abc123",
        data_snapshot_id="snapshot_1",
        config_json={"signal": "ai_adoption_score"},
        created_at="2025-04-04T00:00:00Z",
    )

    assert panel_row.prediction_date == date(2025, 4, 3)
    assert panel_row.available_at <= datetime(2025, 4, 3, tzinfo=panel_row.available_at.tzinfo)
    assert model_run.git_commit == "abc123"
    assert model_run.config_json["signal"] == "ai_adoption_score"


def test_required_column_contracts_cover_csv_loaders() -> None:
    assert {"ticker", "company_name", "snapshot_date"}.issubset(
        MODEL_REQUIRED_COLUMNS["larridin_scores"]
    )
    assert {"ticker", "price_date", "adjusted_close"}.issubset(
        MODEL_REQUIRED_COLUMNS["market_prices"]
    )
    assert {"ticker", "fiscal_quarter", "fiscal_period_end"}.issubset(
        MODEL_REQUIRED_COLUMNS["financial_metrics"]
    )

    validate_required_columns("market_prices", ["ticker", "price_date", "adjusted_close"])
    with pytest.raises(ValueError, match="missing required columns"):
        validate_required_columns("market_prices", ["ticker", "price_date"])
