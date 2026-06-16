from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ai_impact_research.processing.identifiers import (  # noqa: E402
    normalize_company_master,
    summarize_company_master,
    validate_identifier_mapping,
    write_company_master,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a normalized company identifier master.")
    parser.add_argument("--input", required=True, help="Input company master CSV.")
    parser.add_argument(
        "--output",
        default="data/processed/companies_normalized.csv",
        help="Output CSV or Parquet path for normalized company master.",
    )
    args = parser.parse_args()

    raw = pd.read_csv(args.input, dtype={"cik": str})
    companies = normalize_company_master(raw)
    write_company_master(companies, args.output)
    summary = summarize_company_master(companies)
    report = validate_identifier_mapping(companies)

    print("Company master validation summary")
    print(f"companies: {summary['companies']}")
    print(f"tickers: {summary['tickers']}")
    print(f"ciks: {summary['ciks']}")
    print(f"sectors: {summary['sectors']}")
    print(f"missing_sector: {report['missing_sector']}")
    print(f"duplicate_mapping: {report['duplicate_mapping']}")
    print(f"output: {Path(args.output)}")


if __name__ == "__main__":
    main()
