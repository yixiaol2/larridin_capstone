from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_FINANCIAL_COLUMNS = [
    "fiscal_quarter",
    "fiscal_period_end",
    "available_at",
    "revenue",
]
IDENTIFIER_COLUMNS = ["company_id", "ticker"]
MARGIN_COLUMNS = ["gross_margin", "operating_margin"]
NORMALIZED_FINANCIAL_COLUMNS = [
    "company_id",
    "ticker",
    "fiscal_quarter",
    "fiscal_period_end",
    "available_at",
    "revenue",
    "gross_margin",
    "operating_margin",
    "net_income",
    "employee_count",
    "source_name",
    "source_document_id",
]


class SECCompanyFactsAdapter:
    """Future SEC EDGAR company facts adapter placeholder.

    TODO: Add implementation only after SEC request policy, user-agent handling,
    concept mapping, and local caching strategy are defined.
    """

    def fetch_company_facts(self, cik: str) -> pd.DataFrame:
        raise NotImplementedError(
            "TODO: SEC EDGAR ingestion is not implemented. Use CSV ingestion for MVP."
        )


class FinancialDataAPIClient:
    """Future public/vendor financial data adapter placeholder."""

    def fetch_financials(self, *args: Any, **kwargs: Any) -> pd.DataFrame:
        raise NotImplementedError(
            "TODO: Financial API ingestion is not implemented. Use CSV ingestion for MVP."
        )


def load_financials_csv(
    path: str | Path,
    allow_early_available_at: bool = False,
) -> pd.DataFrame:
    df = pd.read_csv(path)
    return normalize_financials(df, allow_early_available_at=allow_early_available_at)


def normalize_financials(
    df: pd.DataFrame,
    allow_early_available_at: bool = False,
) -> pd.DataFrame:
    _validate_financial_columns(df)
    out = df.copy()

    if "company_id" not in out.columns:
        out["company_id"] = None
    if "ticker" not in out.columns:
        out["ticker"] = None
    out["ticker"] = out["ticker"].astype("string").str.upper().str.strip()
    out["company_id"] = out["company_id"].astype("string").str.strip()
    out["fiscal_quarter"] = out["fiscal_quarter"].astype(str).str.upper().str.strip()
    out["fiscal_period_end"] = _parse_datetime_column(out, "fiscal_period_end").dt.date
    out["available_at"] = _parse_datetime_column(out, "available_at")

    period_end_ts = pd.to_datetime(out["fiscal_period_end"])
    early_mask = out["available_at"] < period_end_ts
    if early_mask.any():
        rows = out.loc[early_mask, ["company_id", "ticker", "fiscal_quarter", "available_at"]].to_dict(
            "records"
        )
        message = f"available_at precedes fiscal_period_end for financial records: {rows}"
        if allow_early_available_at:
            warnings.warn(message, UserWarning, stacklevel=2)
        else:
            raise ValueError(message)

    out["revenue"] = _parse_numeric_column(out, "revenue")
    for col in MARGIN_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
        else:
            out[col] = _normalize_margin(out[col], col)

    if "net_income" not in out.columns:
        out["net_income"] = pd.NA
    else:
        out["net_income"] = _parse_numeric_column(out, "net_income")

    if "employee_count" not in out.columns:
        out["employee_count"] = pd.NA
    else:
        out["employee_count"] = pd.to_numeric(out["employee_count"], errors="raise")
        invalid_employee_count = out["employee_count"].notna() & (out["employee_count"] <= 0)
        if invalid_employee_count.any():
            bad = out.loc[invalid_employee_count, ["ticker", "fiscal_quarter", "employee_count"]].to_dict(
                "records"
            )
            raise ValueError(f"employee_count must be positive when present: {bad}")

    if "source_name" not in out.columns:
        out["source_name"] = "financial_export"
    if "source_document_id" not in out.columns:
        out["source_document_id"] = None

    duplicate_mask = out.duplicated(["company_id", "ticker", "fiscal_quarter", "source_name"], keep=False)
    if duplicate_mask.any():
        duplicates = out.loc[
            duplicate_mask, ["company_id", "ticker", "fiscal_quarter", "source_name"]
        ].to_dict("records")
        raise ValueError(f"Duplicate financial records detected: {duplicates}")

    return out[NORMALIZED_FINANCIAL_COLUMNS].sort_values(
        ["company_id", "ticker", "fiscal_quarter"], na_position="last"
    ).reset_index(drop=True)


def write_financials(df: pd.DataFrame, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".parquet":
        df.to_parquet(path, index=False)
    elif path.suffix.lower() == ".csv":
        df.to_csv(path, index=False)
    else:
        raise ValueError("Output path must end with .csv or .parquet")
    return path


def summarize_financials(df: pd.DataFrame) -> dict[str, int]:
    return {
        "rows": int(len(df)),
        "tickers": int(df["ticker"].dropna().nunique()),
        "companies": int(df["company_id"].dropna().nunique()),
        "quarters": int(df["fiscal_quarter"].dropna().nunique()),
    }


def _validate_financial_columns(df: pd.DataFrame) -> None:
    missing = set(REQUIRED_FINANCIAL_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Financial file is missing required columns: {sorted(missing)}")
    if not any(col in df.columns for col in IDENTIFIER_COLUMNS):
        raise ValueError("Financial file must include at least one of company_id or ticker")


def _parse_datetime_column(df: pd.DataFrame, column: str) -> pd.Series:
    try:
        return pd.to_datetime(df[column], errors="raise")
    except Exception as exc:
        raise ValueError(f"Unable to parse {column} as dates") from exc


def _parse_numeric_column(df: pd.DataFrame, column: str) -> pd.Series:
    try:
        return pd.to_numeric(df[column], errors="raise")
    except Exception as exc:
        raise ValueError(f"Unable to parse {column} as numeric") from exc


def _normalize_margin(values: pd.Series, column: str) -> pd.Series:
    numeric = pd.to_numeric(values, errors="raise")
    invalid_negative = numeric.notna() & (numeric < 0)
    if invalid_negative.any():
        bad = values.loc[invalid_negative].to_list()
        raise ValueError(f"{column} must be non-negative: {bad}")
    over_one = numeric > 1
    numeric.loc[over_one] = numeric.loc[over_one] / 100
    invalid_after_normalization = numeric.notna() & (numeric > 1)
    if invalid_after_normalization.any():
        bad = values.loc[invalid_after_normalization].to_list()
        raise ValueError(f"{column} must be a ratio or percentage from 0 to 100: {bad}")
    return numeric
