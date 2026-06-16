from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ai_impact_research.ingestion.market_data import (  # noqa: E402
    load_market_prices_csv,
    summarize_market_prices,
    write_market_prices,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize market price CSV exports.")
    parser.add_argument("--input", required=True, help="Input CSV containing market prices.")
    parser.add_argument(
        "--output",
        default="data/processed/market_prices_normalized.csv",
        help="Output CSV or Parquet path for normalized market prices.",
    )
    args = parser.parse_args()

    prices = load_market_prices_csv(args.input)
    write_market_prices(prices, args.output)
    summary = summarize_market_prices(prices)

    print("Market data validation summary")
    print(f"rows: {summary['rows']}")
    print(f"tickers: {summary['tickers']}")
    print(f"companies: {summary['companies']}")
    print(f"output: {Path(args.output)}")


if __name__ == "__main__":
    main()
