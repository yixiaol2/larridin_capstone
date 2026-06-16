from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ai_impact_research.processing.panel_builder import (  # noqa: E402
    PanelBuilder,
    summarize_panel,
    write_panel,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a point-in-time company-quarter analytical panel.")
    parser.add_argument("--companies", required=True, help="Companies CSV or Parquet input.")
    parser.add_argument("--scores", required=True, help="Larridin scores CSV or Parquet input.")
    parser.add_argument("--prices", required=True, help="Market prices CSV or Parquet input.")
    parser.add_argument("--financials", required=True, help="Financial metrics CSV or Parquet input.")
    parser.add_argument(
        "--output",
        default="data/processed/analytic_panel.csv",
        help="Output CSV or Parquet path.",
    )
    parser.add_argument(
        "--mode",
        choices=["strict", "permissive"],
        default="strict",
        help="Strict drops timing violations; permissive preserves and flags them.",
    )
    args = parser.parse_args()

    panel = PanelBuilder(strict=args.mode == "strict").build(
        _read_table(args.companies, dtype={"cik": str}),
        _read_table(args.scores),
        _read_table(args.prices),
        _read_table(args.financials),
    )
    output = write_panel(panel, args.output)
    summary = summarize_panel(panel)

    print("Analytic panel summary")
    print(f"rows: {summary['rows']}")
    print(f"companies: {summary['companies']}")
    print(f"quarters: {summary['quarters']}")
    print(f"timing_violations: {summary['timing_violations']}")
    print("missingness:")
    for column, count in summary["missingness"].items():
        print(f"  {column}: {count}")
    print(f"output: {output}")


def _read_table(path: str | Path, **kwargs) -> pd.DataFrame:
    table_path = Path(path)
    suffix = table_path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(table_path)
    if suffix == ".csv":
        return pd.read_csv(table_path, **kwargs)
    raise ValueError(f"Input path must end with .csv or .parquet: {table_path}")


if __name__ == "__main__":
    main()
