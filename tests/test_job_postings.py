from __future__ import annotations

import pandas as pd
import pytest

from ai_impact_research.ingestion.job_postings import (
    classify_ai_keyword,
    detect_likely_duplicates,
    normalize_job_postings,
)


def test_job_posting_normalization_hashes_raw_text_and_uppercases_ticker() -> None:
    raw = pd.DataFrame(
        [
            {
                "job_posting_id": "job-1",
                "ticker": "aiva",
                "title": "  Senior ML Engineer  ",
                "description": "Build machine learning systems.",
                "collected_at": "2025-05-01T12:00:00Z",
                "source_name": "synthetic_jobs",
            }
        ]
    )

    normalized = normalize_job_postings(raw)

    assert normalized.loc[0, "ticker"] == "AIVA"
    assert normalized.loc[0, "title"] == "Senior ML Engineer"
    assert len(normalized.loc[0, "raw_hash"]) == 64
    assert normalized.loc[0, "is_ai_keyword_matched"] is True


def test_job_posting_requires_company_id_or_ticker_and_collected_at() -> None:
    raw = pd.DataFrame(
        [
            {
                "job_posting_id": "job-1",
                "title": "Analyst",
                "collected_at": "2025-05-01",
                "source_name": "synthetic_jobs",
            }
        ]
    )

    with pytest.raises(ValueError, match="company_id or ticker"):
        normalize_job_postings(raw)

    with pytest.raises(ValueError, match="collected_at"):
        normalize_job_postings(
            pd.DataFrame(
                [
                    {
                        "job_posting_id": "job-1",
                        "ticker": "AIVA",
                        "title": "Analyst",
                        "source_name": "synthetic_jobs",
                    }
                ]
            )
        )


def test_duplicate_detection_uses_raw_hash_and_company_context() -> None:
    raw = pd.DataFrame(
        [
            {
                "job_posting_id": "job-1",
                "ticker": "AIVA",
                "title": "Data Scientist",
                "description": "Build machine learning models.",
                "collected_at": "2025-05-01",
                "source_name": "synthetic_jobs",
            },
            {
                "job_posting_id": "job-2",
                "ticker": "aiva",
                "title": "data scientist",
                "description": "Build machine learning models.",
                "collected_at": "2025-05-02",
                "source_name": "synthetic_jobs",
            },
            {
                "job_posting_id": "job-3",
                "ticker": "BRIO",
                "title": "Data Scientist",
                "description": "Build machine learning models.",
                "collected_at": "2025-05-02",
                "source_name": "synthetic_jobs",
            },
        ]
    )

    normalized = normalize_job_postings(raw)
    duplicates = detect_likely_duplicates(normalized)

    assert normalized["is_likely_duplicate"].tolist() == [False, True, False]
    assert len(duplicates) == 1
    assert duplicates.loc[0, "job_posting_id"] == "job-2"


def test_ai_keyword_classifier_matches_configurable_terms() -> None:
    assert classify_ai_keyword("Prompt Engineer", "", keywords=["prompt engineer"])
    assert classify_ai_keyword("", "Work on LLM applications.")
    assert not classify_ai_keyword("Store Manager", "Lead retail associates.")
