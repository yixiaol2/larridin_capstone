from __future__ import annotations

import subprocess
import sys

import pandas as pd
import pytest

from ai_impact_research.processing.identifiers import (
    attach_company_id,
    join_on_company_id,
    join_on_ticker,
    normalize_cik,
    normalize_company_master,
    normalize_ticker,
    validate_identifier_mapping,
)


def _companies_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "company_id": ["C001", "C002"],
            "company_name": ["Aiva Systems Inc.", "Brio Retail Group"],
            "ticker": [" aiva ", "brio"],
            "cik": [1001, "0000001002"],
            "exchange": ["nasdaq", "nyse"],
            "sector": ["Information Technology", "Consumer Discretionary"],
            "industry": ["Application Software", "Specialty Retail"],
        }
    )


def test_ticker_normalization_works() -> None:
    assert normalize_ticker(" brk.b ") == "BRK.B"
    normalized = normalize_company_master(_companies_df())
    assert normalized["ticker"].to_list() == ["AIVA", "BRIO"]
    assert normalized["exchange"].to_list() == ["NASDAQ", "NYSE"]


def test_cik_normalization_works() -> None:
    assert normalize_cik(1001) == "0000001001"
    assert normalize_cik(" 1002 ") == "0000001002"
    assert normalize_company_master(_companies_df())["cik"].to_list() == [
        "0000001001",
        "0000001002",
    ]


def test_duplicate_ticker_detection_works() -> None:
    companies = _companies_df()
    companies.loc[1, "ticker"] = "AIVA"
    with pytest.raises(ValueError, match="Duplicate ticker"):
        normalize_company_master(companies)


def test_duplicate_company_id_detection_works() -> None:
    companies = _companies_df()
    companies.loc[1, "company_id"] = "C001"
    with pytest.raises(ValueError, match="Duplicate company_id"):
        normalize_company_master(companies)


def test_conflicting_mapping_detection_works() -> None:
    incoming = pd.DataFrame({"company_id": ["C001"], "ticker": ["BRIO"], "value": [1]})
    with pytest.raises(ValueError, match="Conflicting mapping"):
        attach_company_id(incoming, _companies_df())


def test_join_on_company_id_prefers_stable_key() -> None:
    left = pd.DataFrame({"company_id": ["C001"], "value": [10]})
    right = normalize_company_master(_companies_df())[["company_id", "sector"]]
    joined = join_on_company_id(left, right)
    assert joined.loc[0, "sector"] == "Information Technology"


def test_join_on_ticker_warns_when_used_as_fallback() -> None:
    left = pd.DataFrame({"ticker": ["aiva"], "value": [10]})
    right = normalize_company_master(_companies_df())[["company_id", "ticker"]]
    with pytest.warns(UserWarning, match="Falling back to ticker join"):
        joined = join_on_ticker(left, right)
    assert joined.loc[0, "company_id"] == "C001"
    assert joined.loc[0, "ticker"] == "AIVA"


def test_many_to_many_join_is_prevented() -> None:
    left = pd.DataFrame({"ticker": ["AIVA", "AIVA"], "value": [10, 11]})
    right = pd.DataFrame({"ticker": ["AIVA", "AIVA"], "company_id": ["C001", "C009"]})
    with pytest.warns(UserWarning, match="Falling back to ticker join"):
        with pytest.raises(ValueError, match="many-to-many"):
            join_on_ticker(left, right)


def test_missing_sector_warning_works() -> None:
    companies = _companies_df()
    companies.loc[1, "sector"] = None
    report = validate_identifier_mapping(companies)
    assert report["missing_sector"] == 1
    assert "BRIO" in report["missing_sector_tickers"]


def test_validation_reports_unmatched_rows_between_datasets() -> None:
    report = validate_identifier_mapping(
        _companies_df(),
        datasets={"scores": pd.DataFrame({"ticker": ["AIVA", "MISS"]})},
    )
    assert report["unmatched_rows"]["scores"] == 1
    assert report["unmatched_tickers"]["scores"] == ["MISS"]


def test_build_company_master_cli_writes_normalized_output(tmp_path) -> None:
    input_path = tmp_path / "companies.csv"
    output_path = tmp_path / "companies_normalized.csv"
    _companies_df().to_csv(input_path, index=False)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_company_master.py",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Company master validation summary" in result.stdout
    assert "companies: 2" in result.stdout
    written = pd.read_csv(output_path, dtype={"cik": str})
    assert written["ticker"].to_list() == ["AIVA", "BRIO"]
    assert written["cik"].to_list() == ["0000001001", "0000001002"]
