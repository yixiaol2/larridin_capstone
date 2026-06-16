from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import pandas as pd

COMPANY_MASTER_COLUMNS = [
    "company_id",
    "company_name",
    "ticker",
    "cik",
    "exchange",
    "sector",
    "industry",
    "country",
    "active_from",
    "active_to",
]
COMPANY_MASTER_REQUIRED_COLUMNS = {"company_id", "ticker"}
COMPANY_NAME_COLUMNS = ("company_name", "name")


def normalize_ticker(value: object) -> str | None:
    if _is_missing(value):
        return None
    ticker = str(value).strip().upper()
    return ticker or None


def normalize_cik(value: object) -> str | None:
    if _is_missing(value):
        return None
    cik = str(value).strip()
    if cik.endswith(".0") and cik[:-2].isdigit():
        cik = cik[:-2]
    if not cik.isdigit():
        raise ValueError(f"CIK must contain only digits when provided: {value!r}")
    return cik.zfill(10)


def normalize_company_master(df: pd.DataFrame) -> pd.DataFrame:
    _validate_company_master_columns(df)
    out = df.copy()

    if "company_name" not in out.columns:
        out["company_name"] = out["name"]
    if "name" not in out.columns:
        out["name"] = out["company_name"]

    out["company_id"] = out["company_id"].map(_normalize_text)
    out["company_name"] = out["company_name"].map(_normalize_text)
    out["name"] = out["company_name"]
    out["ticker"] = out["ticker"].map(normalize_ticker)

    for column in ["exchange", "country"]:
        if column not in out.columns:
            out[column] = None
        else:
            out[column] = out[column].map(normalize_ticker)

    for column in ["sector", "industry"]:
        if column not in out.columns:
            out[column] = None
        else:
            out[column] = out[column].map(_normalize_text)

    if "cik" not in out.columns:
        out["cik"] = None
    else:
        out["cik"] = out["cik"].map(normalize_cik)

    for column in ["active_from", "active_to"]:
        if column not in out.columns:
            out[column] = None
        else:
            out[column] = _parse_optional_date(out[column], column)

    _raise_on_missing_required_values(out)
    _raise_on_duplicate_company_ids(out)
    _raise_on_duplicate_tickers(out)
    _raise_on_duplicate_ciks(out)

    ordered = [*COMPANY_MASTER_COLUMNS, "name"]
    passthrough = [col for col in out.columns if col not in ordered]
    return out[[*ordered, *passthrough]].sort_values("ticker").reset_index(drop=True)


def normalize_companies(df: pd.DataFrame) -> pd.DataFrame:
    return normalize_company_master(df)


def validate_identifier_mapping(
    companies: pd.DataFrame,
    datasets: dict[str, pd.DataFrame] | None = None,
) -> dict[str, Any]:
    raw_companies = companies.copy()
    report: dict[str, Any] = {
        "missing_company_id": _count_missing(raw_companies, "company_id"),
        "missing_ticker": _count_missing(raw_companies, "ticker"),
        "missing_sector": _count_missing(raw_companies, "sector"),
        "missing_sector_tickers": [],
        "duplicate_mapping": 0,
        "duplicate_company_ids": [],
        "duplicate_tickers": [],
        "unmatched_rows": {},
        "unmatched_tickers": {},
    }

    if "ticker" in raw_companies.columns:
        normalized_tickers = raw_companies["ticker"].map(normalize_ticker)
        if "sector" in raw_companies.columns:
            missing_sector = raw_companies["sector"].map(_is_missing)
            report["missing_sector_tickers"] = sorted(
                normalized_tickers.loc[missing_sector].dropna().unique().tolist()
            )
        report["duplicate_tickers"] = _duplicate_values(normalized_tickers)
    if "company_id" in raw_companies.columns:
        company_ids = raw_companies["company_id"].map(_normalize_text)
        report["duplicate_company_ids"] = _duplicate_values(company_ids)

    report["duplicate_mapping"] = len(report["duplicate_company_ids"]) + len(report["duplicate_tickers"])

    companies_norm = normalize_company_master(companies)
    if datasets:
        known_company_ids = set(companies_norm["company_id"].dropna())
        known_tickers = set(companies_norm["ticker"].dropna())
        for name, dataset in datasets.items():
            unmatched_mask = _unmatched_dataset_mask(dataset, known_company_ids, known_tickers)
            report["unmatched_rows"][name] = int(unmatched_mask.sum())
            if "ticker" in dataset.columns:
                tickers = dataset["ticker"].map(normalize_ticker)
                report["unmatched_tickers"][name] = sorted(tickers.loc[unmatched_mask].dropna().unique().tolist())
            else:
                report["unmatched_tickers"][name] = []

    return report


def join_on_company_id(
    left: pd.DataFrame,
    right: pd.DataFrame,
    how: str = "left",
    suffixes: tuple[str, str] = ("", "_right"),
) -> pd.DataFrame:
    _require_columns(left, {"company_id"}, "left")
    _require_columns(right, {"company_id"}, "right")
    left_norm = left.copy()
    right_norm = right.copy()
    left_norm["company_id"] = left_norm["company_id"].map(_normalize_text)
    right_norm["company_id"] = right_norm["company_id"].map(_normalize_text)
    _raise_if_many_to_many(left_norm, right_norm, "company_id")
    return left_norm.merge(
        right_norm,
        on="company_id",
        how=how,
        suffixes=suffixes,
        validate=_merge_validation(left_norm, right_norm, "company_id"),
    )


def join_on_ticker(
    left: pd.DataFrame,
    right: pd.DataFrame,
    how: str = "left",
    suffixes: tuple[str, str] = ("", "_right"),
) -> pd.DataFrame:
    warnings.warn(
        "Falling back to ticker join; prefer company_id when available and audit unmatched rows.",
        UserWarning,
        stacklevel=2,
    )
    _require_columns(left, {"ticker"}, "left")
    _require_columns(right, {"ticker"}, "right")
    left_norm = left.copy()
    right_norm = right.copy()
    left_norm["ticker"] = left_norm["ticker"].map(normalize_ticker)
    right_norm["ticker"] = right_norm["ticker"].map(normalize_ticker)
    _raise_if_many_to_many(left_norm, right_norm, "ticker")
    return left_norm.merge(
        right_norm,
        on="ticker",
        how=how,
        suffixes=suffixes,
        validate=_merge_validation(left_norm, right_norm, "ticker"),
    )


def attach_company_id(df: pd.DataFrame, companies: pd.DataFrame) -> pd.DataFrame:
    companies_norm = normalize_company_master(companies)
    out = df.copy()
    if "ticker" in out.columns:
        out["ticker"] = out["ticker"].map(normalize_ticker)
    if "company_id" in out.columns:
        out["company_id"] = out["company_id"].map(_normalize_text)
        if out["company_id"].notna().any():
            _raise_on_conflicting_incoming_mapping(out, companies_norm)
            known_company_ids = set(companies_norm["company_id"])
            unknown = sorted(out.loc[out["company_id"].notna() & ~out["company_id"].isin(known_company_ids), "company_id"].unique())
            if unknown:
                raise ValueError(f"Unable to map company_id values: {unknown}")
            if out["company_id"].notna().all():
                return out

    if "ticker" not in out.columns:
        raise ValueError("Dataset must include company_id or ticker for company mapping")

    right = companies_norm[["company_id", "ticker"]]
    mapped = join_on_ticker(out.drop(columns=["company_id"], errors="ignore"), right, how="left")
    if mapped["company_id"].isna().any():
        missing_tickers = sorted(mapped.loc[mapped["company_id"].isna(), "ticker"].dropna().unique())
        raise ValueError(f"Unable to map tickers to company_id: {missing_tickers}")
    return mapped


def write_company_master(df: pd.DataFrame, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".parquet":
        df.to_parquet(path, index=False)
    elif path.suffix.lower() == ".csv":
        df.to_csv(path, index=False)
    else:
        raise ValueError("Output path must end with .csv or .parquet")
    return path


def summarize_company_master(df: pd.DataFrame) -> dict[str, int]:
    return {
        "companies": int(len(df)),
        "tickers": int(df["ticker"].dropna().nunique()),
        "ciks": int(df["cik"].dropna().nunique()) if "cik" in df.columns else 0,
        "sectors": int(df["sector"].dropna().nunique()) if "sector" in df.columns else 0,
        "missing_sector": _count_missing(df, "sector"),
    }


def _validate_company_master_columns(df: pd.DataFrame) -> None:
    missing = COMPANY_MASTER_REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Company master missing required columns: {sorted(missing)}")
    if not any(col in df.columns for col in COMPANY_NAME_COLUMNS):
        raise ValueError("Company master must include company_name or name")


def _raise_on_missing_required_values(df: pd.DataFrame) -> None:
    for column in ["company_id", "company_name", "ticker"]:
        missing = df[column].map(_is_missing)
        if missing.any():
            raise ValueError(f"Company master has missing {column} values")


def _raise_on_duplicate_company_ids(df: pd.DataFrame) -> None:
    duplicates = _duplicate_values(df["company_id"])
    if duplicates:
        raise ValueError(f"Duplicate company_id values detected: {duplicates}")


def _raise_on_duplicate_tickers(df: pd.DataFrame) -> None:
    duplicates = _duplicate_values(df["ticker"])
    if duplicates:
        raise ValueError(f"Duplicate ticker values detected: {duplicates}")


def _raise_on_duplicate_ciks(df: pd.DataFrame) -> None:
    duplicates = _duplicate_values(df["cik"])
    if duplicates:
        raise ValueError(f"Duplicate CIK values detected: {duplicates}")


def _raise_on_conflicting_incoming_mapping(df: pd.DataFrame, companies: pd.DataFrame) -> None:
    if "company_id" not in df.columns or "ticker" not in df.columns:
        return
    lookup = companies.set_index("company_id")["ticker"].to_dict()
    has_both = df["company_id"].notna() & df["ticker"].notna()
    expected = df.loc[has_both, "company_id"].map(lookup)
    conflicts = has_both.copy()
    conflicts.loc[has_both] = expected.notna() & (expected != df.loc[has_both, "ticker"])
    if conflicts.any():
        rows = df.loc[conflicts, ["company_id", "ticker"]].to_dict("records")
        raise ValueError(f"Conflicting mapping between company_id and ticker: {rows}")


def _raise_if_many_to_many(left: pd.DataFrame, right: pd.DataFrame, key: str) -> None:
    if left[key].duplicated().any() and right[key].duplicated().any():
        raise ValueError(f"Refusing many-to-many join on {key}")


def _merge_validation(left: pd.DataFrame, right: pd.DataFrame, key: str) -> str:
    left_many = left[key].duplicated().any()
    right_many = right[key].duplicated().any()
    if left_many and right_many:
        raise ValueError(f"Refusing many-to-many join on {key}")
    if left_many:
        return "many_to_one"
    if right_many:
        return "one_to_many"
    return "one_to_one"


def _unmatched_dataset_mask(
    dataset: pd.DataFrame,
    known_company_ids: set[str],
    known_tickers: set[str],
) -> pd.Series:
    mask = pd.Series(False, index=dataset.index)
    has_identifier = pd.Series(False, index=dataset.index)
    if "company_id" in dataset.columns:
        company_ids = dataset["company_id"].map(_normalize_text)
        company_present = company_ids.notna()
        has_identifier |= company_present
        mask |= company_present & ~company_ids.isin(known_company_ids)
    if "ticker" in dataset.columns:
        tickers = dataset["ticker"].map(normalize_ticker)
        ticker_present = tickers.notna()
        has_identifier |= ticker_present
        mask |= ticker_present & ~tickers.isin(known_tickers)
    return has_identifier & mask


def _require_columns(df: pd.DataFrame, required: set[str], label: str) -> None:
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{label} dataset missing required columns: {sorted(missing)}")


def _duplicate_values(values: pd.Series) -> list[str]:
    clean = values.dropna()
    duplicates = clean[clean.duplicated(keep=False)]
    return sorted(duplicates.unique().tolist())


def _count_missing(df: pd.DataFrame, column: str) -> int:
    if column not in df.columns:
        return len(df)
    return int(df[column].map(_is_missing).sum())


def _normalize_text(value: object) -> str | None:
    if _is_missing(value):
        return None
    text = str(value).strip()
    return text or None


def _parse_optional_date(values: pd.Series, column: str) -> pd.Series:
    non_missing = ~values.map(_is_missing)
    parsed = pd.Series([None] * len(values), index=values.index, dtype="object")
    if non_missing.any():
        try:
            parsed.loc[non_missing] = pd.to_datetime(values.loc[non_missing], errors="raise").dt.date
        except Exception as exc:
            raise ValueError(f"Unable to parse {column} as dates") from exc
    return parsed


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except TypeError:
        return False
    return str(value).strip() in {"", "nan", "None", "<NA>"}
