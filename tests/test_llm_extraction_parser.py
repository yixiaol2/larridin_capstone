from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_impact_research.llm.eval import (
    confidence_distribution,
    duplicate_evidence_count,
    evidence_coverage_rate,
    missing_score_rate,
    schema_validity_rate,
)
from ai_impact_research.llm.extract import MockLLMClient, parse_extraction_payload


def test_parse_extraction_payload_validates_json_string() -> None:
    extraction = MockLLMClient().extract(
        {
            "source_document_id": "doc1",
            "ticker": "AIVA",
            "source_type": "company_web_page",
            "source_date": "2025-04-20",
            "text": "Aiva deployed AI copilots in customer support and trained teams on responsible use.",
        }
    )
    parsed = parse_extraction_payload(extraction.model_dump_json())

    assert parsed.source_document_id == "doc1"
    assert parsed.signal_scores["ai_operational_maturity"].score is not None


def test_evaluation_helpers_report_quality_metrics() -> None:
    client = MockLLMClient()
    good = client.extract(
        {
            "source_document_id": "doc1",
            "ticker": "AIVA",
            "source_type": "company_web_page",
            "source_date": "2025-04-20",
            "text": "Aiva deployed AI copilots in customer support.",
        }
    )
    insufficient = client.extract(
        {
            "source_document_id": "doc2",
            "ticker": "BRIO",
            "source_type": "news_article",
            "source_date": "2025-04-21",
            "text": "Brio opened a new office.",
        }
    )

    payloads = [good.model_dump(), "{bad json"]
    assert schema_validity_rate(payloads) == 0.5
    assert evidence_coverage_rate([good, insufficient]) == 0.5
    assert missing_score_rate([good, insufficient]) > 0
    assert confidence_distribution([good])["count"] > 0
    assert duplicate_evidence_count([good, good]) >= 1


def test_mock_extraction_script_runs_offline(tmp_path) -> None:
    output_path = tmp_path / "mock_outputs.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_llm_extraction_poc.py",
            "--mock",
            "--input",
            "data/samples/source_documents_sample.jsonl",
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "LLM extraction POC summary" in result.stdout
    assert "mode: mock" in result.stdout
    lines = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 2
    first = json.loads(lines[0])
    assert "source_document_id" in first
    assert "signal_scores" in first


def test_prompt_file_exists_and_includes_rubric_anchors() -> None:
    prompt = Path("src/ai_impact_research/llm/prompts/ai_signal_extraction.md").read_text(
        encoding="utf-8"
    )

    assert "Allowed source types" in prompt
    assert "return null" in prompt
    assert "Do not infer beyond evidence" in prompt
    assert "ai_strategy_specificity" in prompt
