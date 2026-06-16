from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ai_impact_research.time_utils import to_calendar_quarter

SCORE_COLUMNS = [
    "ai_adoption_score",
    "ai_fluency_score",
    "ai_impact_score",
    "ai_hiring_score",
]

IDENTIFIER_COLUMNS = ["company_id", "ticker"]
REQUIRED_SCORE_COLUMNS = [
    "snapshot_date",
    "source_name",
    *SCORE_COLUMNS,
]
OPTIONAL_STANDARD_COLUMNS = [
    "company_id",
    "ticker",
    "company_name",
    "source_url",
    "source_reference",
    "available_at",
]
NORMALIZED_COLUMNS = [
    "company_id",
    "ticker",
    "company_name",
    "snapshot_date",
    "score_quarter",
    *SCORE_COLUMNS,
    "source_name",
    "source_url",
    "available_at",
    "available_at_assumption",
    "metadata_json",
]


class LarridinAPIClient:
    """Future API adapter placeholder.

    TODO: Add a real implementation only after sponsor-provided endpoint shape,
    authentication, pagination, and rate-limit behavior are confirmed.
    """

    def fetch_scores(self, *args: Any, **kwargs: Any) -> pd.DataFrame:
        raise NotImplementedError(
            "TODO: Larridin API ingestion is not implemented. Use CSV export ingestion for MVP."
        )


def load_larridin_scores_csv(
    path: str | Path,
    available_at_override: str | None = None,
) -> pd.DataFrame:
    df = pd.read_csv(path)
    return normalize_larridin_scores(df, available_at_override=available_at_override)


def normalize_larridin_scores(
    df: pd.DataFrame,
    available_at_override: str | None = None,
) -> pd.DataFrame:
    _validate_required_columns(df, available_at_override=available_at_override)

    out = df.copy()
    _normalize_identifiers(out)
    out["snapshot_date"] = _parse_datetime_column(out, "snapshot_date").dt.date
    out["score_quarter"] = to_calendar_quarter(pd.Series(out["snapshot_date"]))
    out["available_at_assumption"] = False

    if "available_at" in out.columns:
        out["available_at"] = _parse_datetime_column(out, "available_at")
    else:
        out["available_at"] = pd.Timestamp(available_at_override)
        out["available_at_assumption"] = True

    for col in SCORE_COLUMNS:
        out[col] = _parse_score_column(out, col)

    if "company_id" not in out.columns:
        out["company_id"] = None
    if "ticker" not in out.columns:
        out["ticker"] = None
    if "company_name" not in out.columns:
        out["company_name"] = None
    if "source_url" not in out.columns:
        out["source_url"] = out["source_reference"] if "source_reference" in out.columns else None

    out["metadata_json"] = _build_metadata_json(out)
    return out[NORMALIZED_COLUMNS].reset_index(drop=True)


def write_larridin_scores(
    df: pd.DataFrame,
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        df.to_parquet(path, index=False)
    elif suffix == ".csv":
        df.to_csv(path, index=False)
    else:
        raise ValueError("Output path must end with .csv or .parquet")
    return path


def summarize_larridin_scores(df: pd.DataFrame) -> dict[str, int | str]:
    identifier_col = "ticker" if df["ticker"].notna().any() else "company_id"
    return {
        "rows": int(len(df)),
        "tickers": int(df["ticker"].dropna().nunique()),
        "companies": int(df["company_id"].dropna().nunique()),
        "identifier": identifier_col,
        "available_at_assumptions": int(df["available_at_assumption"].sum()),
    }


def _validate_required_columns(df: pd.DataFrame, available_at_override: str | None) -> None:
    missing = set(REQUIRED_SCORE_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Larridin score file is missing required columns: {sorted(missing)}")
    if not any(col in df.columns for col in IDENTIFIER_COLUMNS):
        raise ValueError("Larridin score file must include at least one of company_id or ticker")
    if "available_at" not in df.columns and not available_at_override:
        raise ValueError(
            "Larridin score file is missing available_at. Pass --available-at YYYY-MM-DD "
            "only when this timing assumption is documented."
        )


def _normalize_identifiers(df: pd.DataFrame) -> None:
    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
        df.loc[df["ticker"].isin(["", "NAN", "NONE"]), "ticker"] = None
    if "company_id" in df.columns:
        df["company_id"] = df["company_id"].astype(str).str.strip()
        df.loc[df["company_id"].isin(["", "nan", "None"]), "company_id"] = None


def _parse_datetime_column(df: pd.DataFrame, column: str) -> pd.Series:
    try:
        return pd.to_datetime(df[column], errors="raise")
    except Exception as exc:
        raise ValueError(f"Unable to parse {column} as dates") from exc


def _parse_score_column(df: pd.DataFrame, column: str) -> pd.Series:
    numeric = pd.to_numeric(df[column], errors="raise")
    non_integer = numeric.notna() & (numeric % 1 != 0)
    if non_integer.any():
        bad_values = df.loc[non_integer, [column]].to_dict("records")
        raise ValueError(f"Larridin score values must be whole numbers in {column}: {bad_values}")
    scores = numeric.astype(int)
    invalid = ~scores.between(1, 5)
    if invalid.any():
        context_cols = [col for col in ["company_id", "ticker", "snapshot_date", column] if col in df.columns]
        bad_values = df.loc[invalid, context_cols].to_dict("records")
        raise ValueError(f"Invalid 1-5 score values in {column}: {bad_values}")
    return scores


def _build_metadata_json(df: pd.DataFrame) -> pd.Series:
    metadata_cols = [
        col
        for col in df.columns
        if col not in set(NORMALIZED_COLUMNS) | {"score_quarter", "available_at_assumption"}
    ]
    if not metadata_cols:
        return pd.Series(["{}"] * len(df), index=df.index)

    rows = []
    for record in df[metadata_cols].to_dict("records"):
        clean = {key: _json_safe(value) for key, value in record.items() if not pd.isna(value)}
        rows.append(json.dumps(clean, sort_keys=True))
    return pd.Series(rows, index=df.index)


def _json_safe(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value
