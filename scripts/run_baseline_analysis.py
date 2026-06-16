from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ai_impact_research.analysis.backtest import run_quintile_backtest  # noqa: E402
from ai_impact_research.analysis.ic import (  # noqa: E402
    DEFAULT_OUTCOMES,
    DEFAULT_SIGNALS,
    compute_ic_by_quarter,
    summarize_ic_results,
)
from ai_impact_research.analysis.regressions import run_regression_grid  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run baseline IC, regression, and quintile analysis.")
    parser.add_argument("--panel", default="data/processed/analytic_panel.csv")
    parser.add_argument("--processed-dir", default="data/processed/analysis")
    parser.add_argument("--report-dir", default="reports/tables")
    parser.add_argument("--signal", default="composite_ai_score")
    parser.add_argument("--outcome", default="fwd_return_1q")
    parser.add_argument("--min-regression-obs", type=int, default=10)
    args = parser.parse_args()

    panel = _read_table(args.panel)
    if "timing_violation" in panel.columns:
        panel = panel.loc[~panel["timing_violation"].astype(bool)].copy()
    signals = [signal for signal in DEFAULT_SIGNALS if signal in panel.columns]
    outcomes = [outcome for outcome in DEFAULT_OUTCOMES if outcome in panel.columns]

    processed_dir = Path(args.processed_dir)
    report_dir = Path(args.report_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    ic_by_quarter = compute_ic_by_quarter(panel, signals=signals, outcomes=outcomes)
    ic_summary = summarize_ic_results(ic_by_quarter)
    regression_results, regression_warnings = run_regression_grid(
        panel,
        signals=signals,
        outcomes=outcomes,
        min_obs=args.min_regression_obs,
    )
    backtest = run_quintile_backtest(panel, args.signal, args.outcome)
    backtest_metrics = pd.DataFrame([{**backtest.metrics, "signal": args.signal, "outcome": args.outcome}])
    backtest_warnings = pd.DataFrame({"warning": backtest.warnings})

    outputs = {
        "ic_by_quarter.csv": ic_by_quarter,
        "ic_summary.csv": ic_summary,
        "regression_results.csv": regression_results,
        "regression_warnings.csv": regression_warnings,
        "backtest_quintile_returns.csv": backtest.quintile_returns,
        "backtest_long_short_returns.csv": backtest.long_short,
        "backtest_metrics.csv": backtest_metrics,
        "backtest_warnings.csv": backtest_warnings,
    }
    for filename, table in outputs.items():
        _write_table(table, processed_dir / filename)
        _write_table(table, report_dir / filename)

    metadata: dict[str, Any] = {
        "created_at": datetime.now(UTC).isoformat(),
        "panel": args.panel,
        "signals": signals,
        "outcomes": outcomes,
        "backtest_signal": args.signal,
        "backtest_outcome": args.outcome,
        "caveat": "Associational research only; not causal evidence or investment advice.",
    }
    (processed_dir / "analysis_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (report_dir / "analysis_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print("Baseline analysis summary")
    print(f"panel_rows: {len(panel)}")
    print(f"signals: {len(signals)}")
    print(f"outcomes: {len(outcomes)}")
    print(f"ic_rows: {len(ic_by_quarter)}")
    print(f"regression_terms: {len(regression_results)}")
    print(f"regression_warnings: {len(regression_warnings)}")
    print(f"backtest_rebalances: {backtest.metrics['number_of_rebalances']}")
    print(f"backtest_cumulative_return: {backtest.metrics['cumulative_return']}")
    print("caveat: Associational research only; not causal evidence or investment advice.")
    print(f"processed_dir: {processed_dir}")
    print(f"report_dir: {report_dir}")


def _read_table(path: str | Path) -> pd.DataFrame:
    table_path = Path(path)
    if table_path.suffix.lower() == ".parquet":
        return pd.read_parquet(table_path)
    if table_path.suffix.lower() == ".csv":
        return pd.read_csv(table_path)
    raise ValueError(f"Panel path must end with .csv or .parquet: {table_path}")


def _write_table(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


if __name__ == "__main__":
    main()
