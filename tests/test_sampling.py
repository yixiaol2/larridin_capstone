from __future__ import annotations

import pandas as pd

from ai_impact_research.processing.sampling import (
    assign_sampling_bucket,
    sample_job_postings,
    summarize_job_posting_sample,
)


def _postings() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "job_posting_id": "ai-1",
                "title": "Machine Learning Engineer",
                "description": "Build model services.",
                "is_ai_keyword_matched": True,
            },
            {
                "job_posting_id": "ai-2",
                "title": "AI Product Manager",
                "description": "Own AI product roadmap.",
                "is_ai_keyword_matched": True,
            },
            {
                "job_posting_id": "tech-1",
                "title": "Software Engineer",
                "description": "Build backend APIs.",
                "is_ai_keyword_matched": False,
            },
            {
                "job_posting_id": "nontech-1",
                "title": "Store Associate",
                "description": "Help customers.",
                "is_ai_keyword_matched": False,
            },
            {
                "job_posting_id": "leader-1",
                "title": "Director of Digital Strategy",
                "description": "Lead technology strategy.",
                "is_ai_keyword_matched": False,
            },
        ]
    )


def test_sampling_buckets_are_assigned_from_title_description_and_ai_flag() -> None:
    buckets = [
        assign_sampling_bucket(row)
        for row in _postings().to_dict("records")
    ]

    assert buckets == [
        "ai_keyword_matched",
        "ai_keyword_matched",
        "technical_non_ai",
        "non_technical",
        "leadership_strategy",
    ]


def test_sampling_is_deterministic_and_never_exceeds_available_rows() -> None:
    first = sample_job_postings(_postings(), per_bucket=3, random_seed=42)
    second = sample_job_postings(_postings(), per_bucket=3, random_seed=42)

    assert first["job_posting_id"].tolist() == second["job_posting_id"].tolist()
    assert len(first) == len(_postings())
    assert first["sample_weight"].gt(0).all()
    assert set(first["random_seed"]) == {42}
    assert first["sampled_at"].notna().all()


def test_sampling_handles_empty_buckets_and_preserves_weights() -> None:
    postings = _postings().query("is_ai_keyword_matched").reset_index(drop=True)
    sampled = sample_job_postings(postings, per_bucket=1, random_seed=7)

    assert len(sampled) == 1
    assert sampled.loc[0, "sampling_bucket"] == "ai_keyword_matched"
    assert sampled.loc[0, "sample_weight"] == 2.0


def test_sample_summary_reports_weighted_ai_share() -> None:
    sample = sample_job_postings(_postings(), per_bucket=1, random_seed=11)
    summary = summarize_job_posting_sample(_postings(), sample)

    assert summary["total_postings"] == 5
    assert summary["ai_keyword_count"] == 2
    assert summary["sample_size"] == len(sample)
    assert 0 <= summary["weighted_ai_share_estimate"] <= 1
    assert "ai_keyword_matched" in summary["sample_share_by_bucket"]
