from __future__ import annotations

import pandas as pd

from ai_impact_research.analysis.regressions import run_pooled_regression


def _panel(n_per_quarter: int = 8) -> pd.DataFrame:
    rows = []
    for quarter in ["2025Q1", "2025Q2"]:
        for i in range(n_per_quarter):
            signal = float(i)
            rows.append(
                {
                    "quarter": quarter,
                    "sector": "Tech" if i % 2 else "Health Care",
                    "composite_ai_score": signal,
                    "future_revenue_growth_qoq": 0.02 + signal * 0.01,
                    "prior_return_1q": 0.01 * i,
                    "revenue_growth_qoq": 0.005 * i,
                    "operating_margin_t": 0.10 + 0.01 * i,
                    "log_market_cap": 9.0 + i,
                }
            )
    return pd.DataFrame(rows)


def test_regression_runs_on_synthetic_data() -> None:
    result = run_pooled_regression(
        _panel(),
        signal="composite_ai_score",
        outcome="future_revenue_growth_qoq",
    )

    assert result.warning is None
    assert result.nobs >= 10
    assert result.r_squared >= 0
    assert "future_revenue_growth_qoq ~ composite_ai_score" in result.formula
    assert {
        "term",
        "coefficient",
        "std_error",
        "t_stat",
        "p_value",
        "conf_low",
        "conf_high",
        "nobs",
        "r_squared",
        "formula",
    }.issubset(result.table.columns)
    signal_row = result.table.loc[result.table["term"].eq("composite_ai_score")].iloc[0]
    assert signal_row["coefficient"] > 0


def test_regression_small_sample_warning_is_clear() -> None:
    result = run_pooled_regression(
        _panel(n_per_quarter=2),
        signal="composite_ai_score",
        outcome="future_revenue_growth_qoq",
        min_obs=10,
    )

    assert result.table.empty
    assert result.warning is not None
    assert "Need at least 10 observations" in result.warning
