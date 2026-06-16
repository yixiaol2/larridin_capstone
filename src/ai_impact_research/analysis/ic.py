from __future__ import annotations

import math
from typing import Any

import pandas as pd
from scipy.stats import spearmanr

DEFAULT_SIGNALS = [
    "ai_adoption_score",
    "ai_fluency_score",
    "ai_impact_score",
    "ai_hiring_score",
    "composite_ai_score",
]

DEFAULT_OUTCOMES = [
    "fwd_return_1q",
    "fwd_return_2q",
    "future_revenue_growth_qoq",
    "future_operating_margin_delta_qoq",
    "future_revenue_per_employee_growth_qoq",
]


def spearman_ic(df: pd.DataFrame, signal: str, outcome: str, min_obs: int = 3) -> float:
    valid = df[[signal, outcome]].dropna()
    if len(valid) < min_obs:
        raise ValueError(f"Need at least {min_obs} valid observations for IC; got {len(valid)}")
    result = spearmanr(valid[signal], valid[outcome])
    return float(result.statistic)


def compute_ic_by_quarter(
    panel: pd.DataFrame,
    signals: list[str] | None = None,
    outcomes: list[str] | None = None,
    quarter_col: str = "quarter",
    min_obs: int = 3,
) -> pd.DataFrame:
    signals = _available_columns(panel, signals or DEFAULT_SIGNALS)
    outcomes = _available_columns(panel, outcomes or DEFAULT_OUTCOMES)
    if quarter_col not in panel.columns and "score_quarter" in panel.columns:
        quarter_col = "score_quarter"

    rows: list[dict[str, Any]] = []
    for signal in signals:
        for outcome in outcomes:
            for quarter, group in panel.groupby(quarter_col, dropna=False):
                valid = group[[signal, outcome]].dropna()
                row: dict[str, Any] = {
                    "signal": signal,
                    "outcome": outcome,
                    "quarter": quarter,
                    "ic": pd.NA,
                    "n_obs": int(len(valid)),
                    "p_value": pd.NA,
                    "status": "ok",
                }
                if len(valid) < min_obs:
                    row["status"] = "too_few_obs"
                elif valid[signal].nunique() < 2 or valid[outcome].nunique() < 2:
                    row["status"] = "constant_input"
                else:
                    result = spearmanr(valid[signal], valid[outcome])
                    row["ic"] = float(result.statistic)
                    row["p_value"] = float(result.pvalue)
                rows.append(row)
    return pd.DataFrame(rows)


def compute_ic_by_period(
    panel: pd.DataFrame,
    signal: str,
    outcome: str,
    period_col: str = "score_quarter",
) -> pd.DataFrame:
    result = compute_ic_by_quarter(
        panel,
        signals=[signal],
        outcomes=[outcome],
        quarter_col=period_col,
    )
    return result.rename(columns={"quarter": "period", "n_obs": "n"})


def summarize_ic_results(ic_results: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if ic_results.empty:
        return pd.DataFrame(
            columns=[
                "signal",
                "outcome",
                "mean_ic",
                "median_ic",
                "ic_std",
                "ic_t_stat",
                "positive_ic_hit_rate",
                "number_of_quarters",
                "total_observations",
            ]
        )

    for (signal, outcome), group in ic_results.groupby(["signal", "outcome"], dropna=False):
        valid = group.loc[group["status"].eq("ok") & group["ic"].notna()].copy()
        ic_values = pd.to_numeric(valid["ic"], errors="coerce").dropna()
        n_quarters = int(len(ic_values))
        ic_std = float(ic_values.std(ddof=1)) if n_quarters > 1 else pd.NA
        if n_quarters > 1 and not pd.isna(ic_std) and ic_std != 0:
            t_stat = float(ic_values.mean() / (ic_std / math.sqrt(n_quarters)))
        else:
            t_stat = pd.NA
        rows.append(
            {
                "signal": signal,
                "outcome": outcome,
                "mean_ic": float(ic_values.mean()) if n_quarters else pd.NA,
                "median_ic": float(ic_values.median()) if n_quarters else pd.NA,
                "ic_std": ic_std,
                "ic_t_stat": t_stat,
                "positive_ic_hit_rate": float((ic_values > 0).mean()) if n_quarters else pd.NA,
                "number_of_quarters": n_quarters,
                "total_observations": int(group["n_obs"].sum()),
            }
        )
    return pd.DataFrame(rows)


def summarize_ic(ic_by_period: pd.DataFrame) -> dict[str, float | int | None]:
    normalized = ic_by_period.rename(columns={"period": "quarter", "n": "n_obs"}).copy()
    if "signal" not in normalized.columns:
        normalized["signal"] = "signal"
    if "outcome" not in normalized.columns:
        normalized["outcome"] = "outcome"
    summary = summarize_ic_results(normalized)
    if summary.empty:
        return {"mean_ic": None, "hit_rate": None, "num_periods": 0}
    first = summary.iloc[0]
    return {
        "mean_ic": None if pd.isna(first["mean_ic"]) else float(first["mean_ic"]),
        "hit_rate": None
        if pd.isna(first["positive_ic_hit_rate"])
        else float(first["positive_ic_hit_rate"]),
        "num_periods": int(first["number_of_quarters"]),
    }


def _available_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    return [column for column in columns if column in df.columns]
