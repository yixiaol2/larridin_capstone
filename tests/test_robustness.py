from __future__ import annotations

import pandas as pd

from ai_impact_research.analysis.robustness import (
    disclosure_bias_proxy,
    lag_sensitivity,
    llm_extraction_reliability,
    missingness_diagnostics,
    missingness_summary,
    sector_neutral_ic,
    size_bucket_analysis,
)


def _panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["A", "B", "C", "D", "E", "F"],
            "sector": ["Tech", "Tech", "Tech", "Retail", "Retail", "Retail"],
            "score_quarter": ["2025Q1"] * 6,
            "ai_adoption_score": [1, 2, 3, 1, 2, None],
            "composite_ai_score": [1, 2, 3, 1, 2, 3],
            "fwd_return_1q": [0.01, 0.02, 0.03, 0.00, 0.01, 0.02],
            "fwd_return_2q": [0.02, 0.03, 0.04, 0.00, 0.01, 0.02],
            "log_market_cap": [1, 2, 3, 4, 5, 6],
        }
    )


def test_missingness_summary_without_group_col() -> None:
    df = pd.DataFrame({"ticker": ["AAA", "BBB"], "value": [1.0, None]})

    summary = missingness_summary(df)

    assert set(summary.columns) == {"field", "missing_rate"}
    assert summary.loc[summary["field"].eq("value"), "missing_rate"].iloc[0] == 0.5


def test_sector_neutral_ic_handles_small_groups() -> None:
    result = sector_neutral_ic(
        _panel(),
        signal="ai_adoption_score",
        outcome="fwd_return_1q",
        min_obs=3,
    )

    assert result["raw_ic"].notna().any()
    assert "sector_neutral_ic" in result.columns
    assert "insufficient_observations" in set(result["status"])


def test_missingness_diagnostics_reports_sector_quarter_signal_outcome() -> None:
    diagnostics = missingness_diagnostics(
        _panel(),
        signals=["ai_adoption_score"],
        outcomes=["fwd_return_1q"],
    )

    assert set(diagnostics["diagnostic_type"]) >= {
        "missingness_by_sector",
        "missingness_by_quarter",
        "missingness_by_signal",
        "missingness_by_outcome",
    }
    concentrated = diagnostics.loc[diagnostics["field"].eq("ai_adoption_score"), "highly_concentrated"]
    assert concentrated.notna().any()


def test_lag_sensitivity_handles_unavailable_outcomes() -> None:
    result = lag_sensitivity(
        _panel(),
        signal="ai_adoption_score",
        outcomes=["fwd_return_1q", "fwd_return_2q", "fwd_return_4q"],
    )

    assert set(result["outcome"]) == {"fwd_return_1q", "fwd_return_2q", "fwd_return_4q"}
    assert "unavailable" in set(result["status"])


def test_size_bucket_analysis_uses_placeholder_when_market_cap_missing() -> None:
    result = size_bucket_analysis(
        _panel().drop(columns=["log_market_cap"]),
        signal="ai_adoption_score",
        outcome="fwd_return_1q",
    )

    assert result["status"].iloc[0] == "market_cap_unavailable"


def test_disclosure_bias_proxy_skips_gracefully_when_inputs_missing() -> None:
    result = disclosure_bias_proxy(_panel(), score_col="ai_adoption_score")

    assert result["status"].iloc[0] == "disclosure_proxy_unavailable"


def test_llm_reliability_diagnostics_skip_gracefully_when_no_data() -> None:
    result = llm_extraction_reliability(None, panel=_panel())

    assert result["status"].iloc[0] == "llm_extractions_unavailable"
