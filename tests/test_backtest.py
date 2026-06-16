from __future__ import annotations

import pandas as pd
import pytest

from ai_impact_research.analysis.backtest import (
    assign_quintiles,
    compute_backtest_metrics,
    long_short_returns,
    quintile_returns,
    run_quintile_backtest,
)


def _panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "quarter": ["2025Q1"] * 10 + ["2025Q2"] * 10,
            "ticker": [f"T{i:02d}" for i in range(20)],
            "composite_ai_score": list(range(10)) + list(range(10)),
            "fwd_return_1q": [x / 100 for x in range(10)] + [x / 200 for x in range(10)],
        }
    )


def test_backtest_quintile_assignment_works() -> None:
    assigned = assign_quintiles(_panel(), "composite_ai_score")

    q1 = assigned.loc[assigned["quarter"].eq("2025Q1"), "signal_quantile"]
    assert sorted(q1.dropna().astype(int).unique().tolist()) == [1, 2, 3, 4, 5]
    assert q1.value_counts().sort_index().tolist() == [2, 2, 2, 2, 2]


def test_long_short_return_calculation_is_correct() -> None:
    q = quintile_returns(_panel(), "composite_ai_score", "fwd_return_1q")
    ls = long_short_returns(q)

    first = ls.loc[ls["quarter"].eq("2025Q1")].iloc[0]
    assert first["long_return"] == pytest.approx(0.085)
    assert first["short_return"] == pytest.approx(0.005)
    assert first["long_short_return"] == pytest.approx(0.08)


def test_backtest_metrics_include_required_outputs() -> None:
    result = run_quintile_backtest(_panel(), "composite_ai_score", "fwd_return_1q")

    metrics = result.metrics
    assert metrics["number_of_rebalances"] == 2
    assert metrics["average_quarterly_return"] > 0
    assert "cumulative_return" in metrics
    assert "max_drawdown" in metrics
    assert not result.long_short.empty


def test_sharpe_ratio_handles_zero_volatility_safely() -> None:
    metrics = compute_backtest_metrics(pd.Series([0.02, 0.02, 0.02]))

    assert metrics["volatility"] == pytest.approx(0.0)
    assert pd.isna(metrics["sharpe_ratio"])


def test_small_sample_warning_is_clear() -> None:
    small = pd.DataFrame(
        {
            "quarter": ["2025Q1"] * 4,
            "composite_ai_score": [1, 2, 3, 4],
            "fwd_return_1q": [0.01, 0.02, 0.03, 0.04],
        }
    )
    result = run_quintile_backtest(small, "composite_ai_score", "fwd_return_1q")

    assert result.quintile_returns.empty
    assert "not enough observations" in result.warnings[0]
