from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SourceType = Literal[
    "sec_filing",
    "earnings_transcript",
    "job_posting",
    "news_article",
    "company_web_page",
]

SignalName = Literal[
    "ai_strategy_specificity",
    "ai_operational_maturity",
    "ai_workforce_training",
    "ai_hiring_intensity",
    "ai_capex_or_infrastructure_signal",
    "ai_productivity_claim",
]

SIGNAL_NAMES: tuple[str, ...] = (
    "ai_strategy_specificity",
    "ai_operational_maturity",
    "ai_workforce_training",
    "ai_hiring_intensity",
    "ai_capex_or_infrastructure_signal",
    "ai_productivity_claim",
)

SOURCE_TYPE_ALIASES = {
    "SEC filing": "sec_filing",
    "sec filing": "sec_filing",
    "sec_filing": "sec_filing",
    "earnings transcript": "earnings_transcript",
    "earnings_transcript": "earnings_transcript",
    "job posting": "job_posting",
    "job_posting": "job_posting",
    "news": "news_article",
    "news article": "news_article",
    "news_article": "news_article",
    "company page": "company_web_page",
    "company web page": "company_web_page",
    "company_page": "company_web_page",
    "company_web_page": "company_web_page",
}

SCHEMA_VERSION = "ai_signal_extraction_schema_v1"
PROMPT_VERSION = "ai_signal_extraction_v1"


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SourceDocument(StrictBaseModel):
    source_document_id: str
    source_type: SourceType
    source_date: date
    text: str = Field(..., min_length=1, max_length=12000)
    company_id: str | None = None
    ticker: str | None = None
    company_name: str | None = None
    source_url: str | None = None

    @field_validator("source_type", mode="before")
    @classmethod
    def normalize_source_type(cls, value: str) -> str:
        return _normalize_source_type(value)

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize_ticker(cls, value: str | None) -> str | None:
        if value is None:
            return None
        ticker = str(value).strip().upper()
        return ticker or None


class EvidenceSpan(StrictBaseModel):
    evidence_id: str
    text: str = Field(..., min_length=5, max_length=500)
    start_char: int | None = Field(None, ge=0)
    end_char: int | None = Field(None, ge=0)
    source_section: str | None = None

    @model_validator(mode="after")
    def validate_offsets(self) -> EvidenceSpan:
        if self.start_char is not None and self.end_char is not None and self.end_char < self.start_char:
            raise ValueError("end_char must be greater than or equal to start_char")
        return self


class SignalScore(StrictBaseModel):
    score: int | None = Field(None, ge=1, le=5)
    confidence: float = Field(..., ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)
    rationale: str | None = Field(None, max_length=500)


class AISignalExtraction(StrictBaseModel):
    source_document_id: str
    source_type: SourceType
    source_date: date
    extraction_created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    model_name: str
    prompt_version: str = PROMPT_VERSION
    schema_version: str = SCHEMA_VERSION
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    signal_scores: dict[SignalName, SignalScore]
    limitations: list[str] = Field(default_factory=list)
    company_id: str | None = None
    ticker: str | None = None
    company_name: str | None = None

    @field_validator("source_type", mode="before")
    @classmethod
    def normalize_source_type(cls, value: str) -> str:
        return _normalize_source_type(value)

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize_ticker(cls, value: str | None) -> str | None:
        if value is None:
            return None
        ticker = str(value).strip().upper()
        return ticker or None

    @model_validator(mode="after")
    def validate_signal_scores_and_evidence(self) -> AISignalExtraction:
        missing = set(SIGNAL_NAMES) - set(self.signal_scores)
        if missing:
            raise ValueError(f"Missing signal scores: {sorted(missing)}")
        evidence_ids = {span.evidence_id for span in self.evidence}
        for signal_name, signal_score in self.signal_scores.items():
            if signal_score.score is not None and not signal_score.evidence_ids:
                raise ValueError(f"{signal_name} has a score but no evidence references")
            unknown_ids = set(signal_score.evidence_ids) - evidence_ids
            if unknown_ids:
                raise ValueError(
                    f"{signal_name} references unknown evidence ids: {sorted(unknown_ids)}"
                )
        if self.company_id is None and self.ticker is None:
            raise ValueError("AISignalExtraction must include company_id or ticker")
        return self


class ExtractionResult(StrictBaseModel):
    source_document: SourceDocument
    extraction: AISignalExtraction
    raw_response: str | None = None
    parser_errors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_source_linkage(self) -> ExtractionResult:
        if self.source_document.source_document_id != self.extraction.source_document_id:
            raise ValueError("source_document_id mismatch between source document and extraction")
        return self


def _normalize_source_type(value: str) -> str:
    normalized = SOURCE_TYPE_ALIASES.get(str(value).strip())
    if normalized is None:
        normalized = SOURCE_TYPE_ALIASES.get(str(value).strip().lower())
    if normalized is None:
        return str(value).strip()
    return normalized
