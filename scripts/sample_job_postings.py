from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ai_impact_research.ingestion.job_postings import (  # noqa: E402
    load_job_postings_csv,
    summarize_job_postings,
    write_job_postings,
)
from ai_impact_research.processing.sampling import (  # noqa: E402
    sample_job_postings,
    summarize_job_posting_sample,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize and sample job postings for AI hiring research.")
    parser.add_argument("--input", default="data/samples/job_postings_sample.csv")
    parser.add_argument("--output", default="data/processed/job_postings_sampled.csv")
    parser.add_argument("--normalized-output", default="data/processed/job_postings_normalized.csv")
    parser.add_argument("--per-bucket", type=int, default=2)
    parser.add_argument("--random-seed", type=int, default=42)
    args = parser.parse_args()

    normalized = load_job_postings_csv(args.input)
    sampled = sample_job_postings(normalized, per_bucket=args.per_bucket, random_seed=args.random_seed)
    normalized_path = write_job_postings(normalized, args.normalized_output)
    sampled_path = write_job_postings(sampled, args.output)

    normalized_summary = summarize_job_postings(normalized)
    sample_summary = summarize_job_posting_sample(normalized, sampled)

    print("Job posting sampling summary")
    print(f"input: {args.input}")
    print(f"normalized_output: {normalized_path}")
    print(f"sample_output: {sampled_path}")
    print(f"total_postings: {sample_summary['total_postings']}")
    print(f"AI_keyword_count: {sample_summary['ai_keyword_count']}")
    print(f"likely_duplicate_count: {normalized_summary['likely_duplicate_count']}")
    print(f"sample_size: {sample_summary['sample_size']}")
    print(f"weighted_AI_share_estimate: {sample_summary['weighted_ai_share_estimate']:.3f}")
    print(
        "sample_share_by_bucket: "
        f"{json.dumps(sample_summary['sample_share_by_bucket'], sort_keys=True)}"
    )


if __name__ == "__main__":
    main()
