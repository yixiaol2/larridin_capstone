from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from ai_impact_research.llm.schemas import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    SIGNAL_NAMES,
    AISignalExtraction,
    EvidenceSpan,
    SignalScore,
    SourceDocument,
)

AI_TERMS = (" ai ", "artificial intelligence", "machine learning", "generative ai", "copilot")


class LLMClient(Protocol):
    model_name: str

    def extract(self, source_document: SourceDocument | dict[str, Any]) -> AISignalExtraction:
        ...


class MockLLMClient:
    model_name = "mock-evidence-extractor-v1"

    def extract(self, source_document: SourceDocument | dict[str, Any]) -> AISignalExtraction:
        doc = (
            source_document
            if isinstance(source_document, SourceDocument)
            else SourceDocument.model_validate(source_document)
        )
        evidence = _extract_mock_evidence(doc.text)
        signal_scores = _mock_signal_scores(doc.text, evidence)
        limitations = []
        if not evidence:
            limitations.append("No explicit AI adoption evidence found in the source text.")
        if any(score.score is None for score in signal_scores.values()):
            limitations.append("Some signal dimensions were null because evidence was insufficient.")

        return AISignalExtraction(
            company_id=doc.company_id,
            ticker=doc.ticker,
            company_name=doc.company_name,
            source_document_id=doc.source_document_id,
            source_type=doc.source_type,
            source_date=doc.source_date,
            model_name=self.model_name,
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
            evidence=evidence,
            signal_scores=signal_scores,
            limitations=limitations,
        )


def parse_extraction_payload(payload: str | dict[str, Any]) -> AISignalExtraction:
    if isinstance(payload, str):
        data = json.loads(payload)
    else:
        data = payload
    return AISignalExtraction.model_validate(data)


def validate_extraction_json(payload: str | dict[str, Any]) -> AISignalExtraction:
    return parse_extraction_payload(payload)


def read_source_documents_jsonl(path: str | Path) -> list[SourceDocument]:
    docs = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                docs.append(SourceDocument.model_validate(json.loads(line)))
            except Exception as exc:
                raise ValueError(f"Invalid source document JSONL row {line_number}: {exc}") from exc
    return docs


def write_extractions_jsonl(extractions: list[AISignalExtraction], path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for extraction in extractions:
            handle.write(extraction.model_dump_json() + "\n")
    return output_path


def extract_documents(
    source_documents: list[SourceDocument],
    client: LLMClient | None = None,
) -> list[AISignalExtraction]:
    llm_client = client or MockLLMClient()
    return [llm_client.extract(document) for document in source_documents]


def extract_ai_signals_offline_stub(
    text: str,
    company: str,
    period: str,
    source_document_id: str,
    source_type: str,
) -> AISignalExtraction:
    document = SourceDocument(
        source_document_id=source_document_id,
        ticker=company.upper().replace(" ", "")[:5],
        company_name=company,
        source_type=source_type,
        source_date=f"{period[:4]}-12-31" if len(period) >= 4 and period[:4].isdigit() else "2025-01-01",
        text=text,
    )
    return MockLLMClient().extract(document)


def _extract_mock_evidence(text: str) -> list[EvidenceSpan]:
    lowered = f" {text.lower()} "
    if not any(term in lowered for term in AI_TERMS):
        return []
    sentences = [sentence.strip() for sentence in text.strip().split(".") if sentence.strip()]
    quote = ""
    for sentence in sentences:
        sentence_lowered = f" {sentence.lower()} "
        if any(term in sentence_lowered for term in AI_TERMS):
            quote = sentence[:300]
            break
    if not quote:
        quote = text.strip()[:300]
    start = text.find(quote) if quote else None
    return [
        EvidenceSpan(
            evidence_id="ev1",
            text=quote,
            start_char=start if start is not None and start >= 0 else None,
            end_char=(start + len(quote)) if start is not None and start >= 0 else None,
            source_section=None,
        )
    ]


def _mock_signal_scores(text: str, evidence: list[EvidenceSpan]) -> dict[str, SignalScore]:
    lowered = text.lower()
    if not evidence:
        return {
            signal: SignalScore(score=None, confidence=0.0, evidence_ids=[], rationale=None)
            for signal in SIGNAL_NAMES
        }

    def score_for(keywords: tuple[str, ...], base: int = 2) -> SignalScore:
        matched = [keyword for keyword in keywords if keyword in lowered]
        if not matched:
            return SignalScore(score=None, confidence=0.15, evidence_ids=[], rationale=None)
        score = min(5, base + len(matched))
        return SignalScore(
            score=score,
            confidence=0.65 + min(0.25, len(matched) * 0.05),
            evidence_ids=["ev1"],
            rationale=f"Matched evidence keywords: {', '.join(matched[:3])}",
        )

    return {
        "ai_strategy_specificity": score_for(("strategy", "roadmap", "initiative", "deployed")),
        "ai_operational_maturity": score_for(("deployed", "production", "workflow", "pilot")),
        "ai_workforce_training": score_for(("training", "trained", "upskilling", "responsible use")),
        "ai_hiring_intensity": score_for(("hiring", "job", "recruiting", "engineer"), base=1),
        "ai_capex_or_infrastructure_signal": score_for(
            ("infrastructure", "gpu", "data center", "capex", "cloud"), base=1
        ),
        "ai_productivity_claim": score_for(
            ("productivity", "efficiency", "cost savings", "reduced", "automated"), base=1
        ),
    }
