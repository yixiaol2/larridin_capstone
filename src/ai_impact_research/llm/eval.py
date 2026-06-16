from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd

from ai_impact_research.llm.extract import parse_extraction_payload
from ai_impact_research.llm.schemas import AISignalExtraction


def schema_validity_rate(payloads: list[str | dict[str, Any] | AISignalExtraction]) -> float:
    if not payloads:
        return 0.0
    valid = 0
    for payload in payloads:
        try:
            if isinstance(payload, AISignalExtraction):
                valid += 1
            else:
                parse_extraction_payload(payload)
                valid += 1
        except Exception:
            continue
    return valid / len(payloads)


def evidence_coverage_rate(extractions: list[AISignalExtraction]) -> float:
    if not extractions:
        return 0.0
    return sum(1 for extraction in extractions if extraction.evidence) / len(extractions)


def evidence_coverage(extractions: list[AISignalExtraction]) -> float:
    return evidence_coverage_rate(extractions)


def missing_score_rate(extractions: list[AISignalExtraction]) -> float:
    total = 0
    missing = 0
    for extraction in extractions:
        for score in extraction.signal_scores.values():
            total += 1
            if score.score is None:
                missing += 1
    if total == 0:
        return 0.0
    return missing / total


def confidence_distribution(extractions: list[AISignalExtraction]) -> dict[str, float | int | None]:
    values = [
        score.confidence
        for extraction in extractions
        for score in extraction.signal_scores.values()
        if score.confidence is not None
    ]
    if not values:
        return {"count": 0, "mean": None, "median": None, "min": None, "max": None}
    series = pd.Series(values)
    return {
        "count": int(len(series)),
        "mean": float(series.mean()),
        "median": float(series.median()),
        "min": float(series.min()),
        "max": float(series.max()),
    }


def duplicate_evidence_detection(extractions: list[AISignalExtraction]) -> list[dict[str, Any]]:
    evidence_texts = [
        span.text.strip().lower()
        for extraction in extractions
        for span in extraction.evidence
        if span.text.strip()
    ]
    counts = Counter(evidence_texts)
    return [
        {"evidence_text": evidence_text, "count": count}
        for evidence_text, count in counts.items()
        if count > 1
    ]


def duplicate_evidence_count(extractions: list[AISignalExtraction]) -> int:
    return len(duplicate_evidence_detection(extractions))
