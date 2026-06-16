from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ai_impact_research.ingestion.financials import (  # noqa: E402
    load_financials_csv,
    summarize_financials,
    write_financials,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize financial fundamentals CSV exports.")
    parser.add_argument("--input", required=True, help="Input CSV containing financial fundamentals.")
    parser.add_argument(
        "--output",
        default="data/processed/financial_metrics_normalized.csv",
        help="Output CSV or Parquet path for normalized financial metrics.",
    )
    parser.add_argument(
        "--allow-early-available-at",
        action="store_true",
        help=(
            "Allow available_at values before fiscal_period_end and emit a warning. "
            "Use only for synthetic data or explicitly documented sponsor timing assumptions."
        ),
    )
    args = parser.parse_args()

    financials = load_financials_csv(
        args.input,
        allow_early_available_at=args.allow_early_available_at,
    )
    write_financials(financials, args.output)
    summary = summarize_financials(financials)

    print("Financial fundamentals validation summary")
    print(f"rows: {summary['rows']}")
    print(f"tickers: {summary['tickers']}")
    print(f"companies: {summary['companies']}")
    print(f"quarters: {summary['quarters']}")
    print(f"output: {Path(args.output)}")


if __name__ == "__main__":
    main()
