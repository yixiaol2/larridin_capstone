from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ai_impact_research.analysis.robustness import (  # noqa: E402
    append_interim_findings_summary,
    run_robustness_checks,
    write_robustness_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run robustness and responsible AI diagnostics.")
    parser.add_argument("--panel", default="data/processed/analytic_panel.csv")
    parser.add_argument("--signal", default="composite_ai_score")
    parser.add_argument("--outcome", default="fwd_return_1q")
    parser.add_argument("--llm-extractions", default="data/processed/llm_extractions_sample.jsonl")
    parser.add_argument("--processed-output", default="data/processed/analysis/robustness_summary.csv")
    parser.add_argument("--report-output", default="reports/tables/robustness_summary.csv")
    parser.add_argument("--append-report", default="reports/interim_findings.md")
    args = parser.parse_args()

    panel = pd.read_csv(args.panel)
    llm_path = Path(args.llm_extractions)
    summary = run_robustness_checks(
        panel,
        signal=args.signal,
        outcome=args.outcome,
        llm_extractions=llm_path if llm_path.exists() else None,
    )
    processed_path, report_path = write_robustness_outputs(
        summary,
        processed_output=args.processed_output,
        report_output=args.report_output,
    )
    append_path = append_interim_findings_summary(summary, args.append_report)

    print("Robustness diagnostics summary")
    print(f"panel: {args.panel}")
    print(f"rows: {len(summary)}")
    print(f"diagnostics: {', '.join(sorted(summary['diagnostic'].dropna().unique()))}")
    print(f"processed_output: {processed_path}")
    print(f"report_output: {report_path}")
    print(f"markdown_summary: {append_path}")


if __name__ == "__main__":
    main()
