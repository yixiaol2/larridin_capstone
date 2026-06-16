from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

SAMPLING_BUCKETS = [
    "ai_keyword_matched",
    "technical_non_ai",
    "non_technical",
    "leadership_strategy",
]
TECHNICAL_KEYWORDS = [
    "software",
    "engineer",
    "developer",
    "data engineer",
    "cloud",
    "platform",
    "backend",
    "frontend",
    "devops",
    "security",
    "analytics",
    "database",
]
LEADERSHIP_STRATEGY_KEYWORDS = [
    "director",
    "vp",
    "vice president",
    "chief",
    "head of",
    "strategy",
    "strategic",
    "transformation",
]


def assign_sampling_bucket(row: pd.Series | dict[str, Any]) -> str:
    is_ai = bool(_get(row, "is_ai_keyword_matched", False))
    title = str(_get(row, "title", "") or "").lower()
    description = str(_get(row, "description", "") or "").lower()
    text = f"{title} {description}"

    if is_ai:
        return "ai_keyword_matched"
    if any(keyword in text for keyword in LEADERSHIP_STRATEGY_KEYWORDS):
        return "leadership_strategy"
    if any(keyword in text for keyword in TECHNICAL_KEYWORDS):
        return "technical_non_ai"
    return "non_technical"


def sample_job_postings(
    df: pd.DataFrame,
    per_bucket: int = 25,
    random_seed: int = 0,
) -> pd.DataFrame:
    if per_bucket < 0:
        raise ValueError("per_bucket must be non-negative")
    if df.empty or per_bucket == 0:
        return _empty_sample(df, random_seed)

    out = df.copy()
    if "sampling_bucket" not in out.columns:
        out["sampling_bucket"] = out.apply(assign_sampling_bucket, axis=1)

    sampled_parts = []
    sampled_at = datetime.now(UTC).isoformat()
    for bucket_index, bucket in enumerate(SAMPLING_BUCKETS):
        bucket_df = out.loc[out["sampling_bucket"] == bucket].copy()
        available = len(bucket_df)
        sample_size = min(per_bucket, available)
        if sample_size == 0:
            continue
        sampled = bucket_df.sample(n=sample_size, random_state=random_seed + bucket_index)
        sampled["sample_weight"] = available / sample_size
        sampled["random_seed"] = random_seed
        sampled["sampled_at"] = sampled_at
        sampled_parts.append(sampled)

    if not sampled_parts:
        return _empty_sample(out, random_seed)
    return pd.concat(sampled_parts).reset_index(drop=True)


def summarize_job_posting_sample(
    full_postings: pd.DataFrame,
    sampled_postings: pd.DataFrame,
) -> dict[str, Any]:
    full = full_postings.copy()
    sample = sampled_postings.copy()
    if "sampling_bucket" not in full.columns and not full.empty:
        full["sampling_bucket"] = full.apply(assign_sampling_bucket, axis=1)
    if "sampling_bucket" not in sample.columns and not sample.empty:
        sample["sampling_bucket"] = sample.apply(assign_sampling_bucket, axis=1)

    sample_share_by_bucket = (
        sample["sampling_bucket"].value_counts(normalize=True).sort_index().to_dict()
        if not sample.empty
        else {}
    )
    weighted_ai_share = _weighted_ai_share(sample)
    ai_count = (
        int(full["is_ai_keyword_matched"].fillna(False).sum())
        if "is_ai_keyword_matched" in full.columns
        else int((full["sampling_bucket"] == "ai_keyword_matched").sum())
    )
    return {
        "total_postings": int(len(full)),
        "ai_keyword_count": ai_count,
        "sample_size": int(len(sample)),
        "sample_share_by_bucket": {key: float(value) for key, value in sample_share_by_bucket.items()},
        "weighted_ai_share_estimate": weighted_ai_share,
    }


def _weighted_ai_share(sample: pd.DataFrame) -> float:
    if sample.empty:
        return 0.0
    weights = (
        pd.to_numeric(sample["sample_weight"], errors="raise")
        if "sample_weight" in sample.columns
        else pd.Series(1.0, index=sample.index)
    )
    if "is_ai_keyword_matched" in sample.columns:
        ai_flag = sample["is_ai_keyword_matched"].fillna(False).astype(bool)
    else:
        ai_flag = sample["sampling_bucket"] == "ai_keyword_matched"
    denominator = weights.sum()
    if denominator == 0:
        return 0.0
    return float(weights.loc[ai_flag].sum() / denominator)


def _empty_sample(df: pd.DataFrame, random_seed: int) -> pd.DataFrame:
    out = df.copy().iloc[0:0]
    for column in ["sampling_bucket", "sample_weight", "random_seed", "sampled_at"]:
        if column not in out.columns:
            out[column] = pd.Series(dtype="object")
    out["random_seed"] = out["random_seed"].astype("object")
    return out


def _get(row: pd.Series | dict[str, Any], key: str, default: Any = None) -> Any:
    if isinstance(row, pd.Series):
        return row.get(key, default)
    return row.get(key, default)
