from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ai_impact_research.llm.eval import (  # noqa: E402
    confidence_distribution,
    duplicate_evidence_count,
    evidence_coverage_rate,
    missing_score_rate,
    schema_validity_rate,
)
from ai_impact_research.llm.extract import (  # noqa: E402
    MockLLMClient,
    extract_documents,
    read_source_documents_jsonl,
    write_extractions_jsonl,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline LLM AI signal extraction POC.")
    parser.add_argument("--mock", action="store_true", help="Use deterministic offline mock extractor.")
    parser.add_argument("--input", default="data/samples/source_documents_sample.jsonl")
    parser.add_argument("--output", default="data/processed/llm_extractions_sample.jsonl")
    args = parser.parse_args()

    if not args.mock:
        key_message = "No API key found." if not os.getenv("OPENAI_API_KEY") else "API key found."
        print(
            f"{key_message} Real LLM extraction is not implemented in this POC. "
            "Re-run with --mock for deterministic offline extraction, or add a real "
            "LLMClient adapter in ai_impact_research.llm.extract.",
            file=sys.stderr,
        )
        raise SystemExit(0)

    mode = "mock"
    client = MockLLMClient()
    docs = read_source_documents_jsonl(args.input)
    extractions = extract_documents(docs, client=client)
    output_path = write_extractions_jsonl(extractions, args.output)
    confidence = confidence_distribution(extractions)

    print("LLM extraction POC summary")
    print(f"mode: {mode}")
    print(f"documents: {len(docs)}")
    print(f"extractions: {len(extractions)}")
    print(f"schema_validity_rate: {schema_validity_rate(extractions):.3f}")
    print(f"evidence_coverage_rate: {evidence_coverage_rate(extractions):.3f}")
    print(f"missing_score_rate: {missing_score_rate(extractions):.3f}")
    print(f"confidence_count: {confidence['count']}")
    print(f"confidence_mean: {confidence['mean']}")
    print(f"duplicate_evidence_count: {duplicate_evidence_count(extractions)}")
    print(f"output: {output_path}")


if __name__ == "__main__":
    main()
