from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ai_impact_research.time_utils import to_calendar_quarter

REQUIRED_MARKET_COLUMNS = ["adjusted_close"]
IDENTIFIER_COLUMNS = ["company_id", "ticker"]
DATE_COLUMNS = ["date", "price_date"]
NORMALIZED_MARKET_COLUMNS = [
    "company_id",
    "ticker",
    "price_date",
    "price_quarter",
    "adjusted_close",
    "daily_return",
    "volume",
    "source_name",
    "available_at",
]


class MarketDataAPIClient:
    """Future public market data adapter placeholder.

    TODO: Add implementation only after vendor/source selection, adjusted-price
    semantics, authentication, pagination, and rate limits are defined.
    """

    def fetch_prices(self, *args: Any, **kwargs: Any) -> pd.DataFrame:
        raise NotImplementedError(
            "TODO: Market data API ingestion is not implemented. Use CSV ingestion for MVP."
        )


def load_market_prices_csv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return normalize_market_prices(df)


def normalize_market_prices(df: pd.DataFrame) -> pd.DataFrame:
    _validate_market_columns(df)
    out = df.copy()

    if "date" in out.columns and "price_date" not in out.columns:
        out = out.rename(columns={"date": "price_date"})
    if "company_id" not in out.columns:
        out["company_id"] = None
    if "ticker" not in out.columns:
        out["ticker"] = None

    out["ticker"] = out["ticker"].astype("string").str.upper().str.strip()
    out["company_id"] = out["company_id"].astype("string").str.strip()
    out["price_date"] = _parse_datetime_column(out, "price_date").dt.date
    out["price_quarter"] = to_calendar_quarter(pd.Series(out["price_date"]))
    out["adjusted_close"] = _parse_numeric_column(out, "adjusted_close")
    if (out["adjusted_close"] <= 0).any():
        bad = out.loc[out["adjusted_close"] <= 0, ["ticker", "price_date", "adjusted_close"]].to_dict(
            "records"
        )
        raise ValueError(f"adjusted_close must be > 0: {bad}")

    if "volume" not in out.columns:
        out["volume"] = pd.NA
    else:
        out["volume"] = pd.to_numeric(out["volume"], errors="coerce")
    if "source_name" not in out.columns:
        out["source_name"] = "market_data_export"
    if "available_at" not in out.columns:
        out["available_at"] = pd.to_datetime(out["price_date"])
    else:
        out["available_at"] = _parse_datetime_column(out, "available_at")

    sort_cols = ["company_id", "ticker", "price_date"]
    out = out.sort_values(sort_cols, na_position="last").reset_index(drop=True)
    entity_key = out["company_id"].where(out["company_id"].notna(), out["ticker"])
    out["daily_return"] = out.groupby(entity_key, dropna=False)["adjusted_close"].pct_change()

    duplicate_mask = out.duplicated(["company_id", "ticker", "price_date", "source_name"], keep=False)
    if duplicate_mask.any():
        duplicates = out.loc[
            duplicate_mask, ["company_id", "ticker", "price_date", "source_name"]
        ].to_dict("records")
        raise ValueError(f"Duplicate market price records detected: {duplicates}")

    return out[NORMALIZED_MARKET_COLUMNS]


def write_market_prices(df: pd.DataFrame, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".parquet":
        df.to_parquet(path, index=False)
    elif path.suffix.lower() == ".csv":
        df.to_csv(path, index=False)
    else:
        raise ValueError("Output path must end with .csv or .parquet")
    return path


def summarize_market_prices(df: pd.DataFrame) -> dict[str, int]:
    return {
        "rows": int(len(df)),
        "tickers": int(df["ticker"].dropna().nunique()),
        "companies": int(df["company_id"].dropna().nunique()),
    }


def _validate_market_columns(df: pd.DataFrame) -> None:
    missing = set(REQUIRED_MARKET_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Market data file is missing required columns: {sorted(missing)}")
    if not any(col in df.columns for col in IDENTIFIER_COLUMNS):
        raise ValueError("Market data file must include at least one of company_id or ticker")
    if not any(col in df.columns for col in DATE_COLUMNS):
        raise ValueError("Market data file must include date or price_date")


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
