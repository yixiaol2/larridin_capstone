from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_PROCESSED_DIR = Path("data/processed")
DEFAULT_ANALYSIS_DIR = DEFAULT_PROCESSED_DIR / "analysis"
REQUIRED_SETUP_COMMANDS = [
    "python scripts/bootstrap_from_samples.py",
    "python scripts/build_panel.py",
    "python scripts/run_baseline_analysis.py",
]
SIGNAL_COLUMNS = [
    "ai_adoption_score",
    "ai_fluency_score",
    "ai_impact_score",
    "ai_hiring_score",
    "composite_ai_score",
]
OUTCOME_COLUMNS = [
    "fwd_return_1q",
    "fwd_return_2q",
    "fwd_excess_return_1q",
    "future_revenue_growth_qoq",
    "future_operating_margin_delta_qoq",
    "future_revenue_per_employee_growth_qoq",
]


@dataclass(frozen=True)
class DashboardData:
    panel: pd.DataFrame
    ic_summary: pd.DataFrame
    ic_by_quarter: pd.DataFrame
    regression_results: pd.DataFrame
    backtest_metrics: pd.DataFrame
    backtest_quintile_returns: pd.DataFrame
    backtest_long_short_returns: pd.DataFrame
    panel_path: Path
    analysis_dir: Path
    missing_files: list[str]


def load_dashboard_data_cached(
    panel_path: str = "data/processed/analytic_panel.csv",
    analysis_dir: str = "data/processed/analysis",
) -> DashboardData:
    return load_dashboard_data(panel_path=Path(panel_path), analysis_dir=Path(analysis_dir))


def load_dashboard_data(
    panel_path: str | Path | None = None,
    analysis_dir: str | Path | None = None,
) -> DashboardData:
    panel_path = Path(panel_path) if panel_path is not None else DEFAULT_PROCESSED_DIR / "analytic_panel.csv"
    analysis_dir = Path(analysis_dir) if analysis_dir is not None else DEFAULT_ANALYSIS_DIR
    missing_files: list[str] = []

    panel = _read_optional_table(panel_path, "panel", missing_files)
    return DashboardData(
        panel=panel,
        ic_summary=_read_optional_table(analysis_dir / "ic_summary.csv", "ic_summary", missing_files),
        ic_by_quarter=_read_optional_table(
            analysis_dir / "ic_by_quarter.csv", "ic_by_quarter", missing_files
        ),
        regression_results=_read_optional_table(
            analysis_dir / "regression_results.csv", "regression_results", missing_files
        ),
        backtest_metrics=_read_optional_table(
            analysis_dir / "backtest_metrics.csv", "backtest_metrics", missing_files
        ),
        backtest_quintile_returns=_read_optional_table(
            analysis_dir / "backtest_quintile_returns.csv",
            "backtest_quintile_returns",
            missing_files,
        ),
        backtest_long_short_returns=_read_optional_table(
            analysis_dir / "backtest_long_short_returns.csv",
            "backtest_long_short_returns",
            missing_files,
        ),
        panel_path=panel_path,
        analysis_dir=analysis_dir,
        missing_files=missing_files,
    )


def summarize_panel(panel: pd.DataFrame) -> dict[str, Any]:
    if panel.empty:
        return {
            "company_count": 0,
            "quarter_count": 0,
            "sector_count": 0,
            "row_count": 0,
            "sector_coverage": pd.DataFrame(columns=["sector", "company_count"]),
            "missingness": {},
        }
    company_col = "company_id" if "company_id" in panel.columns else "ticker"
    quarter_col = "score_quarter" if "score_quarter" in panel.columns else "quarter"
    missing_cols = [
        col
        for col in [*SIGNAL_COLUMNS, *OUTCOME_COLUMNS, "sector", quarter_col]
        if col in panel.columns
    ]
    sector_coverage = (
        panel.groupby("sector", dropna=False)[company_col]
        .nunique()
        .rename("company_count")
        .reset_index()
        .sort_values("company_count", ascending=False)
    ) if "sector" in panel.columns else pd.DataFrame(columns=["sector", "company_count"])

    return {
        "company_count": int(panel[company_col].dropna().nunique()) if company_col in panel.columns else 0,
        "quarter_count": int(panel[quarter_col].dropna().nunique()) if quarter_col in panel.columns else 0,
        "sector_count": int(panel["sector"].dropna().nunique()) if "sector" in panel.columns else 0,
        "row_count": int(len(panel)),
        "sector_coverage": sector_coverage,
        "missingness": {col: int(panel[col].isna().sum()) for col in missing_cols},
    }


def available_signals(panel: pd.DataFrame) -> list[str]:
    return [col for col in SIGNAL_COLUMNS if col in panel.columns]


def available_outcomes(panel: pd.DataFrame) -> list[str]:
    return [col for col in OUTCOME_COLUMNS if col in panel.columns]


def setup_instructions() -> str:
    commands = "\n".join(f"- `{command}`" for command in REQUIRED_SETUP_COMMANDS)
    return f"Processed dashboard inputs are missing. Run:\n\n{commands}"


def _read_optional_table(path: Path, label: str, missing_files: list[str]) -> pd.DataFrame:
    if not path.exists():
        missing_files.append(label)
        return pd.DataFrame()
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)
