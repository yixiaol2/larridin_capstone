from __future__ import annotations

import subprocess
import sys
import warnings

import pandas as pd
import pytest

from ai_impact_research.ingestion.financials import (
    FinancialDataAPIClient,
    SECCompanyFactsAdapter,
    load_financials_csv,
    normalize_financials,
)


def _financials_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": [" msft "],
            "fiscal_quarter": ["2025q1"],
            "fiscal_period_end": ["2025-03-31"],
            "available_at": ["2025-04-25"],
            "revenue": ["1000.0"],
            "gross_margin": [62.0],
            "operating_margin": [0.25],
            "net_income": [180.0],
            "employee_count": [100.0],
            "source_name": ["synthetic_fundamentals_sample"],
            "source_document_id": ["doc_1"],
        }
    )


def test_good_financial_input_passes_and_normalizes_margins() -> None:
    out = normalize_financials(_financials_df())

    assert out.loc[0, "ticker"] == "MSFT"
    assert out.loc[0, "fiscal_quarter"] == "2025Q1"
    assert out.loc[0, "gross_margin"] == pytest.approx(0.62)
    assert out.loc[0, "operating_margin"] == pytest.approx(0.25)
    assert out.loc[0, "revenue"] == pytest.approx(1000.0)


def test_missing_available_at_fails() -> None:
    df = _financials_df().drop(columns=["available_at"])

    with pytest.raises(ValueError, match="available_at"):
        normalize_financials(df)


def test_available_at_before_period_end_raises_by_default() -> None:
    df = _financials_df()
    df.loc[0, "available_at"] = "2025-03-01"

    with pytest.raises(ValueError, match="available_at"):
        normalize_financials(df)


def test_available_at_before_period_end_can_warn_when_allowed() -> None:
    df = _financials_df()
    df.loc[0, "available_at"] = "2025-03-01"

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = normalize_financials(df, allow_early_available_at=True)

    assert out.loc[0, "available_at"] == pd.Timestamp("2025-03-01")
    assert any("available_at" in str(item.message) for item in caught)


def test_invalid_employee_count_fails() -> None:
    df = _financials_df()
    df.loc[0, "employee_count"] = 0

    with pytest.raises(ValueError, match="employee_count"):
        normalize_financials(df)


def test_non_numeric_revenue_fails() -> None:
    df = _financials_df()
    df.loc[0, "revenue"] = "not-a-number"

    with pytest.raises(ValueError, match="revenue"):
        normalize_financials(df)


def test_financial_cli_writes_normalized_output(tmp_path) -> None:
    input_path = tmp_path / "fundamentals.csv"
    output_path = tmp_path / "financial_metrics_normalized.csv"
    _financials_df().to_csv(input_path, index=False)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/ingest_financials.py",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    out = pd.read_csv(output_path)

    assert "rows: 1" in result.stdout
    assert "tickers: 1" in result.stdout
    assert out.loc[0, "gross_margin"] == pytest.approx(0.62)


def test_load_financials_csv_reads_file(tmp_path) -> None:
    input_path = tmp_path / "fundamentals.csv"
    _financials_df().to_csv(input_path, index=False)

    out = load_financials_csv(input_path)

    assert out.loc[0, "ticker"] == "MSFT"


def test_future_api_stubs_do_not_call_network() -> None:
    with pytest.raises(NotImplementedError, match="TODO"):
        SECCompanyFactsAdapter().fetch_company_facts("0000000000")
    with pytest.raises(NotImplementedError, match="TODO"):
        FinancialDataAPIClient().fetch_financials()
