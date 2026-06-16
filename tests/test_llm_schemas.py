from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from ai_impact_research.llm.schemas import (
    AISignalExtraction,
    EvidenceSpan,
    ExtractionResult,
    SignalScore,
    SourceDocument,
)


def _source_document() -> SourceDocument:
    return SourceDocument(
        source_document_id="doc_sample_001",
        company_id="C001",
        ticker="AIVA",
        source_type="earnings_transcript",
        source_date="2025-04-20",
        text="We deployed AI assistants for support workflows after a limited pilot.",
    )


def _valid_extraction() -> AISignalExtraction:
    evidence = [
        EvidenceSpan(
            evidence_id="ev1",
            text="deployed AI assistants for support workflows",
            start_char=3,
            end_char=45,
            source_section="prepared remarks",
        )
    ]
    return AISignalExtraction(
        company_id="C001",
        ticker="AIVA",
        source_document_id="doc_sample_001",
        source_type="earnings_transcript",
        source_date="2025-04-20",
        model_name="mock-llm",
        prompt_version="ai_signal_extraction_v1",
        schema_version="ai_signal_extraction_schema_v1",
        evidence=evidence,
        signal_scores={
            "ai_strategy_specificity": SignalScore(score=3, confidence=0.72, evidence_ids=["ev1"]),
            "ai_operational_maturity": SignalScore(score=4, confidence=0.70, evidence_ids=["ev1"]),
            "ai_workforce_training": SignalScore(score=None, confidence=0.15, evidence_ids=[]),
            "ai_hiring_intensity": SignalScore(score=None, confidence=0.10, evidence_ids=[]),
            "ai_capex_or_infrastructure_signal": SignalScore(
                score=None, confidence=0.10, evidence_ids=[]
            ),
            "ai_productivity_claim": SignalScore(score=None, confidence=0.10, evidence_ids=[]),
        },
        limitations=["No quantified productivity result in source."],
    )


def test_schema_validation_passes_for_valid_extraction() -> None:
    extraction = _valid_extraction()

    assert extraction.source_date == date(2025, 4, 20)
    assert extraction.signal_scores["ai_operational_maturity"].score == 4
    result = ExtractionResult(source_document=_source_document(), extraction=extraction)
    assert result.extraction.source_document_id == result.source_document.source_document_id


def test_invalid_score_range_fails() -> None:
    with pytest.raises(ValidationError):
        SignalScore(score=6, confidence=0.5, evidence_ids=["ev1"])


def test_missing_evidence_allowed_when_scores_are_null() -> None:
    extraction = AISignalExtraction(
        ticker="AIVA",
        source_document_id="doc_sample_001",
        source_type="news_article",
        source_date="2025-04-20",
        model_name="mock-llm",
        prompt_version="ai_signal_extraction_v1",
        schema_version="ai_signal_extraction_schema_v1",
        evidence=[],
        signal_scores={
            "ai_strategy_specificity": SignalScore(score=None, confidence=0.0, evidence_ids=[]),
            "ai_operational_maturity": SignalScore(score=None, confidence=0.0, evidence_ids=[]),
            "ai_workforce_training": SignalScore(score=None, confidence=0.0, evidence_ids=[]),
            "ai_hiring_intensity": SignalScore(score=None, confidence=0.0, evidence_ids=[]),
            "ai_capex_or_infrastructure_signal": SignalScore(
                score=None, confidence=0.0, evidence_ids=[]
            ),
            "ai_productivity_claim": SignalScore(score=None, confidence=0.0, evidence_ids=[]),
        },
        limitations=["Source does not contain AI adoption evidence."],
    )

    assert not extraction.evidence
    assert extraction.signal_scores["ai_strategy_specificity"].score is None


def test_non_null_score_requires_evidence_reference() -> None:
    with pytest.raises(ValueError, match="evidence"):
        AISignalExtraction(
            ticker="AIVA",
            source_document_id="doc_sample_001",
            source_type="news_article",
            source_date="2025-04-20",
            model_name="mock-llm",
            prompt_version="ai_signal_extraction_v1",
            schema_version="ai_signal_extraction_schema_v1",
            evidence=[],
            signal_scores={
                "ai_strategy_specificity": SignalScore(score=2, confidence=0.3, evidence_ids=[]),
                "ai_operational_maturity": SignalScore(score=None, confidence=0.0, evidence_ids=[]),
                "ai_workforce_training": SignalScore(score=None, confidence=0.0, evidence_ids=[]),
                "ai_hiring_intensity": SignalScore(score=None, confidence=0.0, evidence_ids=[]),
                "ai_capex_or_infrastructure_signal": SignalScore(
                    score=None, confidence=0.0, evidence_ids=[]
                ),
                "ai_productivity_claim": SignalScore(score=None, confidence=0.0, evidence_ids=[]),
            },
            limitations=[],
        )
