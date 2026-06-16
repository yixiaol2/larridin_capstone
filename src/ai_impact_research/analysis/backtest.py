from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class BacktestResult:
    assigned_panel: pd.DataFrame
    quintile_returns: pd.DataFrame
    long_short: pd.DataFrame
    metrics: dict[str, Any]
    warnings: list[str]


def assign_quintiles(
    df: pd.DataFrame,
    signal: str,
    period_col: str = "quarter",
    quantiles: int = 5,
    label_col: str = "signal_quantile",
    min_obs_per_period: int | None = None,
) -> pd.DataFrame:
    if period_col not in df.columns and "score_quarter" in df.columns:
        period_col = "score_quarter"
    min_obs_per_period = min_obs_per_period or quantiles
    out = df.copy()
    out[label_col] = pd.NA
    for _period, idx in out.groupby(period_col).groups.items():
        valid_idx = out.loc[idx, signal].dropna().index
        if len(valid_idx) < min_obs_per_period:
            continue
        ranks = out.loc[valid_idx, signal].rank(method="first")
        try:
            out.loc[valid_idx, label_col] = pd.qcut(ranks, q=quantiles, labels=False) + 1
        except ValueError:
            continue
    return out


def assign_quantiles(
    df: pd.DataFrame,
    signal: str,
    period_col: str = "score_quarter",
    quantiles: int = 5,
    label_col: str = "signal_quantile",
) -> pd.DataFrame:
    return assign_quintiles(df, signal, period_col, quantiles, label_col)


def quintile_returns(
    panel: pd.DataFrame,
    signal: str,
    return_col: str = "fwd_return_1q",
    period_col: str = "quarter",
    quantiles: int = 5,
) -> pd.DataFrame:
    if period_col not in panel.columns and "score_quarter" in panel.columns:
        period_col = "score_quarter"
    assigned = assign_quintiles(panel, signal, period_col, quantiles)
    valid = assigned.dropna(subset=["signal_quantile", return_col]).copy()
    if valid.empty:
        return pd.DataFrame(columns=[period_col, "signal_quantile", "mean_return", "n"])
    valid["signal_quantile"] = valid["signal_quantile"].astype(int)
    grouped = (
        valid.groupby([period_col, "signal_quantile"], observed=True)[return_col]
        .agg(mean_return="mean", n="count")
        .reset_index()
        .rename(columns={period_col: "quarter"})
    )
    return grouped


def long_short_returns(
    quintile_result: pd.DataFrame,
    period_col: str = "quarter",
    low_quantile: int = 1,
    high_quantile: int = 5,
) -> pd.DataFrame:
    if quintile_result.empty:
        return pd.DataFrame(
            columns=["quarter", "long_return", "short_return", "long_short_return", "cumulative_return"]
        )
    q = quintile_result.copy()
    if period_col not in q.columns and "score_quarter" in q.columns:
        period_col = "score_quarter"
    q["signal_quantile"] = q["signal_quantile"].astype(int)
    wide = q.pivot(index=period_col, columns="signal_quantile", values="mean_return")
    if low_quantile not in wide.columns or high_quantile not in wide.columns:
        return pd.DataFrame(
            columns=["quarter", "long_return", "short_return", "long_short_return", "cumulative_return"]
        )
    out = pd.DataFrame(
        {
            "quarter": wide.index.astype(str),
            "long_return": wide[high_quantile].values,
            "short_return": wide[low_quantile].values,
            "long_short_return": (wide[high_quantile] - wide[low_quantile]).values,
        }
    )
    out["cumulative_return"] = (1 + out["long_short_return"].fillna(0)).cumprod() - 1
    return out.reset_index(drop=True)


def compute_backtest_metrics(returns: pd.Series, periods_per_year: int = 4) -> dict[str, Any]:
    valid = pd.to_numeric(returns, errors="coerce").dropna()
    if valid.empty:
        return {
            "cumulative_return": pd.NA,
            "average_quarterly_return": pd.NA,
            "annualized_return": pd.NA,
            "volatility": pd.NA,
            "sharpe_ratio": pd.NA,
            "max_drawdown": pd.NA,
            "hit_rate": pd.NA,
            "number_of_rebalances": 0,
        }

    cumulative_curve = (1 + valid).cumprod()
    cumulative_return = float(cumulative_curve.iloc[-1] - 1)
    average_quarterly_return = float(valid.mean())
    annualized_return = float((1 + average_quarterly_return) ** periods_per_year - 1)
    quarterly_vol = float(valid.std(ddof=1)) if len(valid) > 1 else 0.0
    volatility = quarterly_vol * math.sqrt(periods_per_year)
    sharpe_ratio = annualized_return / volatility if volatility > 0 else pd.NA
    drawdown = cumulative_curve / cumulative_curve.cummax() - 1
    return {
        "cumulative_return": cumulative_return,
        "average_quarterly_return": average_quarterly_return,
        "annualized_return": annualized_return,
        "volatility": float(volatility),
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": float(drawdown.min()),
        "hit_rate": float((valid > 0).mean()),
        "number_of_rebalances": int(len(valid)),
    }


def run_quintile_backtest(
    panel: pd.DataFrame,
    signal: str,
    return_col: str = "fwd_return_1q",
    period_col: str = "quarter",
    quantiles: int = 5,
) -> BacktestResult:
    if period_col not in panel.columns and "score_quarter" in panel.columns:
        period_col = "score_quarter"
    warnings: list[str] = []
    valid = panel.dropna(subset=[signal, return_col]).copy()
    small_periods = [
        str(period)
        for period, group in valid.groupby(period_col)
        if len(group) < quantiles
    ]
    if small_periods:
        warnings.append(
            f"Some periods have not enough observations for {quantiles} quantiles: {small_periods}"
        )
    assigned = assign_quintiles(valid, signal, period_col, quantiles)
    q = quintile_returns(valid, signal, return_col, period_col, quantiles)
    ls = long_short_returns(q)
    metrics = compute_backtest_metrics(ls["long_short_return"] if "long_short_return" in ls.columns else pd.Series(dtype=float))
    return BacktestResult(
        assigned_panel=assigned,
        quintile_returns=q,
        long_short=ls,
        metrics=metrics,
        warnings=warnings,
    )
