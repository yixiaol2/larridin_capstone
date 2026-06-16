import pandas as pd

from ai_impact_research.agent.company_report_agent import generate_company_report


def test_company_report_contains_caveat() -> None:
    panel = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "name": ["AAA Corp"],
            "sector": ["Tech"],
            "industry": ["Software"],
            "score_quarter": ["2025Q1"],
            "ai_adoption_score": [4],
            "ai_fluency_score": [3],
            "ai_impact_score": [3],
            "ai_hiring_score": [4],
            "ai_composite_score": [3.5],
            "fwd_return_1q": [0.1],
            "revenue_growth_qoq": [0.05],
            "operating_margin_delta_qoq": [0.02],
            "revenue_per_employee_t": [10.0],
        }
    )
    report = generate_company_report(panel, "AAA")
    assert "not investment advice" in report.lower()
