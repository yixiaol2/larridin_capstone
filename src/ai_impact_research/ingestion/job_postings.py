from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from ai_impact_research.processing.identifiers import normalize_ticker

REQUIRED_JOB_POSTING_COLUMNS = ["job_posting_id", "title", "collected_at", "source_name"]
IDENTIFIER_COLUMNS = ["company_id", "ticker"]
OPTIONAL_JOB_POSTING_COLUMNS = [
    "department",
    "location",
    "description",
    "posting_date",
    "source_url",
    "is_active",
]
NORMALIZED_JOB_POSTING_COLUMNS = [
    "job_posting_id",
    "company_id",
    "ticker",
    "title",
    "department",
    "location",
    "description",
    "posting_date",
    "collected_at",
    "source_url",
    "source_name",
    "raw_hash",
    "is_active",
    "is_ai_keyword_matched",
    "is_likely_duplicate",
]
DEFAULT_AI_KEYWORDS = [
    "artificial intelligence",
    "machine learning",
    "generative AI",
    "LLM",
    "NLP",
    "computer vision",
    "data scientist",
    "ML engineer",
    "prompt engineer",
    "AI product",
    "AI platform",
    "automation engineer",
]


def load_job_postings_csv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return normalize_job_postings(df)


def normalize_job_postings(
    df: pd.DataFrame,
    ai_keywords: Iterable[str] | None = None,
) -> pd.DataFrame:
    _validate_job_posting_columns(df)
    out = df.copy()

    if "company_id" not in out.columns:
        out["company_id"] = None
    if "ticker" not in out.columns:
        out["ticker"] = None
    for column in OPTIONAL_JOB_POSTING_COLUMNS:
        if column not in out.columns:
            out[column] = pd.NA

    out["job_posting_id"] = out["job_posting_id"].map(_normalize_text)
    out["company_id"] = out["company_id"].map(_normalize_text)
    out["ticker"] = out["ticker"].map(normalize_ticker)
    out["title"] = out["title"].map(_normalize_text)
    out["department"] = out["department"].map(_normalize_text)
    out["location"] = out["location"].map(_normalize_text)
    out["description"] = out["description"].map(_normalize_text)
    out["source_url"] = out["source_url"].map(_normalize_text)
    out["source_name"] = out["source_name"].map(_normalize_text)
    out["collected_at"] = _parse_datetime(out["collected_at"], "collected_at")
    out["posting_date"] = _parse_optional_date(out["posting_date"], "posting_date")
    out["is_active"] = _parse_optional_bool(out["is_active"])
    out["raw_hash"] = out.apply(_hash_job_posting_raw_text, axis=1)
    out["is_ai_keyword_matched"] = out.apply(
        lambda row: classify_ai_keyword(row["title"], row["description"], keywords=ai_keywords),
        axis=1,
    ).map(bool).astype(object)
    out["is_likely_duplicate"] = _likely_duplicate_mask(out).map(bool).astype(object)

    _raise_on_missing_required_values(out)
    return out[NORMALIZED_JOB_POSTING_COLUMNS].reset_index(drop=True)


def classify_ai_keyword(
    title: object,
    description: object = "",
    keywords: Iterable[str] | None = None,
) -> bool:
    text = f"{_normalize_text(title) or ''} {_normalize_text(description) or ''}".lower()
    terms = list(keywords or DEFAULT_AI_KEYWORDS)
    return any(_keyword_matches(text, term) for term in terms)


def detect_likely_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    if "is_likely_duplicate" in df.columns:
        duplicates = df.loc[df["is_likely_duplicate"]].copy()
    else:
        out = df.copy()
        out["is_likely_duplicate"] = _likely_duplicate_mask(out)
        duplicates = out.loc[out["is_likely_duplicate"]].copy()
    return duplicates.reset_index(drop=True)


def write_job_postings(df: pd.DataFrame, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".parquet":
        df.to_parquet(path, index=False)
    elif path.suffix.lower() == ".csv":
        df.to_csv(path, index=False)
    else:
        raise ValueError("Output path must end with .csv or .parquet")
    return path


def summarize_job_postings(df: pd.DataFrame) -> dict[str, int]:
    return {
        "rows": int(len(df)),
        "companies": int(df["company_id"].dropna().nunique()) if "company_id" in df.columns else 0,
        "tickers": int(df["ticker"].dropna().nunique()) if "ticker" in df.columns else 0,
        "ai_keyword_count": int(df["is_ai_keyword_matched"].sum())
        if "is_ai_keyword_matched" in df.columns
        else 0,
        "likely_duplicate_count": int(df["is_likely_duplicate"].sum())
        if "is_likely_duplicate" in df.columns
        else 0,
    }


def _validate_job_posting_columns(df: pd.DataFrame) -> None:
    missing = set(REQUIRED_JOB_POSTING_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Job postings file is missing required columns: {sorted(missing)}")
    if not any(column in df.columns for column in IDENTIFIER_COLUMNS):
        raise ValueError("Job postings file must include at least one of company_id or ticker")


def _raise_on_missing_required_values(df: pd.DataFrame) -> None:
    for column in REQUIRED_JOB_POSTING_COLUMNS:
        if df[column].isna().any():
            raise ValueError(f"Job postings file has missing {column} values")
    missing_identifier = df["company_id"].isna() & df["ticker"].isna()
    if missing_identifier.any():
        raise ValueError("Each job posting must include company_id or ticker")


def _hash_job_posting_raw_text(row: pd.Series) -> str:
    pieces = [
        row.get("title"),
        row.get("department"),
        row.get("location"),
        row.get("description"),
        row.get("source_url"),
    ]
    normalized = " | ".join(_normalize_for_hash(piece) for piece in pieces)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _likely_duplicate_mask(df: pd.DataFrame) -> pd.Series:
    entity_key = df["company_id"].where(df["company_id"].notna(), df["ticker"])
    key = pd.DataFrame({"entity_key": entity_key, "raw_hash": df["raw_hash"]})
    return key.duplicated(["entity_key", "raw_hash"], keep="first")


def _keyword_matches(text: str, keyword: str) -> bool:
    normalized = _normalize_for_hash(keyword)
    if not normalized:
        return False
    pattern = rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])"
    return re.search(pattern, text) is not None


def _parse_datetime(values: pd.Series, column: str) -> pd.Series:
    try:
        return pd.to_datetime(values, errors="raise", utc=True)
    except Exception as exc:
        raise ValueError(f"Unable to parse {column} as datetimes") from exc


def _parse_optional_date(values: pd.Series, column: str) -> pd.Series:
    missing = values.isna() | (values.astype(str).str.strip() == "")
    parsed = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    if (~missing).any():
        try:
            parsed.loc[~missing] = pd.to_datetime(values.loc[~missing], errors="raise").dt.normalize()
        except Exception as exc:
            raise ValueError(f"Unable to parse {column} as dates") from exc
    return parsed.dt.date


def _parse_optional_bool(values: pd.Series) -> pd.Series:
    if values.isna().all():
        return values
    mapping = {
        "true": True,
        "1": True,
        "yes": True,
        "y": True,
        "false": False,
        "0": False,
        "no": False,
        "n": False,
    }
    return values.map(
        lambda value: pd.NA
        if _is_missing(value)
        else mapping.get(str(value).strip().lower(), bool(value))
    )


def _normalize_text(value: object) -> str | None:
    if _is_missing(value):
        return None
    text = re.sub(r"\s+", " ", str(value).strip())
    return text or None


def _normalize_for_hash(value: object) -> str:
    return (_normalize_text(value) or "").lower()


def _is_missing(value: object) -> bool:
    return value is None or value is pd.NA or (isinstance(value, float) and pd.isna(value))
