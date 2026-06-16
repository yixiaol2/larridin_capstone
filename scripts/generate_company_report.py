from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ai_impact_research.agent.company_report_agent import generate_company_report  # noqa: E402
from ai_impact_research.agent.tools import CompanyReportTools, load_panel  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a ticker-level AI impact research report.")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--panel", default="data/processed/analytic_panel.csv")
    parser.add_argument("--output", default=None)
    parser.add_argument("--backtest", default="data/processed/analysis/backtest_metrics.csv")
    parser.add_argument("--evidence", default="data/processed/llm_extractions_sample.jsonl")
    parser.add_argument("--signal", default="composite_ai_score")
    args = parser.parse_args()

    panel = load_panel(args.panel)
    tools = CompanyReportTools(
        panel,
        backtest_path=args.backtest,
        evidence_path=args.evidence,
    )
    report = generate_company_report(tools, args.ticker, signal=args.signal)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(f"Wrote report to {output_path}")
    else:
        print(report)


if __name__ == "__main__":
    main()
