from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_impact_research.ingestion.larridin import (  # noqa: E402
    load_larridin_scores_csv,
    summarize_larridin_scores,
    write_larridin_scores,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize Larridin score CSV export.")
    parser.add_argument("--input", required=True, help="Path to Larridin score CSV export.")
    parser.add_argument(
        "--output",
        default="data/processed/larridin_scores_normalized.csv",
        help="Output path ending in .csv or .parquet.",
    )
    parser.add_argument(
        "--available-at",
        default=None,
        help=(
            "Assumed availability date to use only when the export lacks available_at. "
            "Format: YYYY-MM-DD."
        ),
    )
    args = parser.parse_args()

    df = load_larridin_scores_csv(args.input, available_at_override=args.available_at)
    output = write_larridin_scores(df, args.output)
    summary = summarize_larridin_scores(df)

    print("Larridin score validation summary")
    print(f"rows: {summary['rows']}")
    print(f"tickers: {summary['tickers']}")
    print(f"companies: {summary['companies']}")
    print(f"available_at assumptions: {summary['available_at_assumptions']}")
    print(f"output: {output}")


if __name__ == "__main__":
    main()
