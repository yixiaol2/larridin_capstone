from __future__ import annotations

import pandas as pd
import pytest

from ai_impact_research.analysis.ic import (
    DEFAULT_OUTCOMES,
    DEFAULT_SIGNALS,
    compute_ic_by_quarter,
    summarize_ic_results,
)


def _panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "quarter": ["2025Q1"] * 5 + ["2025Q2"] * 5,
            "ai_adoption_score": [1, 2, 3, 4, 5] * 2,
            "ai_fluency_score": [5, 4, 3, 2, 1] * 2,
            "ai_impact_score": [1, 1, 2, 2, 3] * 2,
            "ai_hiring_score": [2, 2, 3, 4, 5] * 2,
            "composite_ai_score": [1, 2, 3, 4, 5] * 2,
            "fwd_return_1q": [0.01, 0.02, 0.03, 0.04, 0.05] * 2,
            "future_revenue_growth_qoq": [0.02, 0.04, 0.06, 0.08, 0.10] * 2,
        }
    )


def test_ic_returns_expected_positive_sign_on_controlled_data() -> None:
    result = compute_ic_by_quarter(
        _panel(),
        signals=["ai_adoption_score"],
        outcomes=["fwd_return_1q"],
    )

    assert result.loc[0, "signal"] == "ai_adoption_score"
    assert result.loc[0, "outcome"] == "fwd_return_1q"
    assert result["ic"].tolist() == pytest.approx([1.0, 1.0])
    summary = summarize_ic_results(result)
    assert summary.loc[0, "mean_ic"] == pytest.approx(1.0)
    assert summary.loc[0, "positive_ic_hit_rate"] == pytest.approx(1.0)
    assert summary.loc[0, "number_of_quarters"] == 2
    assert summary.loc[0, "total_observations"] == 10


def test_ic_handles_missing_values_and_small_samples() -> None:
    panel = _panel()
    panel.loc[[0, 1, 2], "fwd_return_1q"] = None

    result = compute_ic_by_quarter(
        panel,
        signals=["ai_adoption_score"],
        outcomes=["fwd_return_1q"],
        min_obs=3,
    )

    q1 = result.loc[result["quarter"].eq("2025Q1")].iloc[0]
    q2 = result.loc[result["quarter"].eq("2025Q2")].iloc[0]
    assert q1["n_obs"] == 2
    assert pd.isna(q1["ic"])
    assert q1["status"] == "too_few_obs"
    assert q2["n_obs"] == 5
    assert q2["ic"] == pytest.approx(1.0)


def test_default_signal_and_outcome_lists_include_phase9_columns() -> None:
    assert "composite_ai_score" in DEFAULT_SIGNALS
    assert "future_operating_margin_delta_qoq" in DEFAULT_OUTCOMES
