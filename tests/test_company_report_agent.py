from __future__ import annotations

import pandas as pd

from ai_impact_research.agent.company_report_agent import generate_company_report


def _panel() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "company_id": "C001",
                "company_name": "AAA Corp",
                "sector": "Software",
                "industry": "Application Software",
                "score_quarter": "2025Q2",
                "ai_adoption_score": 4,
                "ai_fluency_score": 3,
                "ai_impact_score": 4,
                "ai_hiring_score": 3,
                "composite_ai_score": 3.5,
                "fwd_return_1q": 0.04,
                "future_revenue_growth_qoq": 0.02,
                "future_operating_margin_delta_qoq": 0.01,
            },
            {
                "ticker": "BBB",
                "company_id": "C002",
                "company_name": "BBB Inc",
                "sector": "Software",
                "industry": "Infrastructure Software",
                "score_quarter": "2025Q2",
                "ai_adoption_score": 2,
                "ai_fluency_score": 2,
                "ai_impact_score": 2,
                "ai_hiring_score": 2,
                "composite_ai_score": 2.0,
                "fwd_return_1q": 0.01,
                "future_revenue_growth_qoq": 0.01,
                "future_operating_margin_delta_qoq": 0.0,
            },
        ]
    )


class MockNarrativeClient:
    def rewrite_report(self, context: dict, draft_report: str) -> str:
        assert context["snapshot"]["ticker"] == "AAA"
        assert "Executive summary" in draft_report
        return draft_report + "\n\n## LLM narrative note\nMock rewrite used provided context only."


def test_templated_report_contains_required_sections() -> None:
    report = generate_company_report(_panel(), "AAA")

    for section in [
        "Executive summary",
        "AI signal profile",
        "Peer comparison",
        "Historical performance context",
        "Signal-to-outcome research context",
        "Evidence excerpts",
        "Caveats and limitations",
        "Non-investment-advice disclaimer",
    ]:
        assert f"## {section}" in report


def test_missing_ticker_report_says_data_unavailable() -> None:
    report = generate_company_report(_panel(), "ZZZ")

    assert "Data is unavailable" in report
    assert "ZZZ" in report


def test_llm_mode_can_be_mocked() -> None:
    report = generate_company_report(_panel(), "AAA", use_llm=True, llm_client=MockNarrativeClient())

    assert "Mock rewrite used provided context only" in report
    assert "not investment advice" in report.lower()


def test_report_does_not_claim_causality_or_investment_advice() -> None:
    report = generate_company_report(_panel(), "AAA")
    lower = report.lower()

    assert "not investment advice" in lower
    assert "does not establish causality" in lower
    assert "caused future performance" not in lower
