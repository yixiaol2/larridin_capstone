from __future__ import annotations

import subprocess
import sys

import pandas as pd

from ai_impact_research.processing.panel_builder import PanelBuilder, build_analytic_panel


def _companies_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "company_id": ["C1", "C2"],
            "ticker": ["AAA", "BBB"],
            "company_name": ["AAA Corp", "BBB Corp"],
            "sector": ["Tech", "Tech"],
            "industry": ["Software", "Hardware"],
            "market_cap": [100.0, 400.0],
        }
    )


def _scores_df(prediction_date: str | None = None) -> pd.DataFrame:
    data = {
        "company_id": ["C1", "C2"],
        "ticker": ["AAA", "BBB"],
        "company_name": ["AAA Corp", "BBB Corp"],
        "snapshot_date": ["2025-03-31", "2025-03-31"],
        "available_at": ["2025-04-02", "2025-04-02"],
        "ai_adoption_score": [4, 2],
        "ai_fluency_score": [3, 3],
        "ai_impact_score": [5, 2],
        "ai_hiring_score": [4, 1],
        "source_name": ["synthetic_larridin_sample", "synthetic_larridin_sample"],
    }
    if prediction_date is not None:
        data["prediction_date"] = [prediction_date, prediction_date]
    return pd.DataFrame(data)


def _prices_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "company_id": ["C1", "C1", "C1", "C1", "C2", "C2", "C2", "C2"],
            "ticker": ["AAA", "AAA", "AAA", "AAA", "BBB", "BBB", "BBB", "BBB"],
            "price_date": [
                "2024-12-31",
                "2025-03-31",
                "2025-06-30",
                "2025-09-30",
                "2024-12-31",
                "2025-03-31",
                "2025-06-30",
                "2025-09-30",
            ],
            "adjusted_close": [90.0, 100.0, 110.0, 121.0, 50.0, 55.0, 60.0, 54.0],
            "available_at": [
                "2024-12-31",
                "2025-03-31",
                "2025-06-30",
                "2025-09-30",
                "2024-12-31",
                "2025-03-31",
                "2025-06-30",
                "2025-09-30",
            ],
        }
    )


def _financials_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "company_id": ["C1", "C1", "C1", "C1", "C2", "C2", "C2", "C2"],
            "ticker": ["AAA", "AAA", "AAA", "AAA", "BBB", "BBB", "BBB", "BBB"],
            "fiscal_quarter": [
                "2024Q4",
                "2025Q1",
                "2025Q2",
                "2025Q3",
                "2024Q4",
                "2025Q1",
                "2025Q2",
                "2025Q3",
            ],
            "fiscal_period_end": [
                "2024-12-31",
                "2025-03-31",
                "2025-06-30",
                "2025-09-30",
                "2024-12-31",
                "2025-03-31",
                "2025-06-30",
                "2025-09-30",
            ],
            "available_at": [
                "2025-01-20",
                "2025-04-01",
                "2025-07-20",
                "2025-10-20",
                "2025-01-20",
                "2025-04-01",
                "2025-07-20",
                "2025-10-20",
            ],
            "revenue": [909.0909, 1000.0, 1100.0, 1210.0, 850.0, 800.0, 760.0, 798.0],
            "operating_margin": [0.18, 0.20, 0.22, 0.25, 0.11, 0.10, 0.09, 0.11],
            "employee_count": [100.0, 100.0, 100.0, 110.0, 50.0, 50.0, 50.0, 55.0],
        }
    )


def test_panel_grain_and_required_columns() -> None:
    panel = build_analytic_panel(_companies_df(), _scores_df(), _prices_df(), _financials_df())

    assert len(panel) == 2
    assert not panel.duplicated(["company_id", "score_quarter"]).any()
    assert {
        "company_id",
        "ticker",
        "company_name",
        "sector",
        "snapshot_date",
        "score_quarter",
        "score_available_at",
        "prediction_date",
        "outcome_start_date",
        "outcome_end_date",
        "quarter",
        "timing_warning",
        "timing_violation",
    }.issubset(panel.columns)


def test_composite_score_calculation() -> None:
    panel = build_analytic_panel(_companies_df(), _scores_df(), _prices_df(), _financials_df())

    aaa = panel.loc[panel["ticker"].eq("AAA")].iloc[0]
    assert aaa["composite_ai_score"] == 4.0


def test_forward_and_prior_returns_are_calculated_after_prediction_date() -> None:
    panel = build_analytic_panel(_companies_df(), _scores_df(), _prices_df(), _financials_df())
    aaa = panel.loc[panel["ticker"].eq("AAA")].iloc[0]

    assert aaa["outcome_start_date"] == pd.Timestamp("2025-06-30").date()
    assert aaa["outcome_end_date"] == pd.Timestamp("2025-09-30").date()
    assert round(aaa["prior_return_1q"], 4) == 0.1111
    assert round(aaa["fwd_return_1q"], 4) == 0.1000
    assert pd.isna(aaa["fwd_return_2q"])


def test_excess_return_uses_sector_average_proxy() -> None:
    panel = build_analytic_panel(_companies_df(), _scores_df(), _prices_df(), _financials_df())
    aaa = panel.loc[panel["ticker"].eq("AAA")].iloc[0]

    # AAA forward return is +10%; BBB forward return is -10%; sector proxy average is 0%.
    assert round(aaa["fwd_excess_return_1q"], 4) == 0.1000


def test_future_fundamentals_align_to_future_periods() -> None:
    panel = build_analytic_panel(_companies_df(), _scores_df(), _prices_df(), _financials_df())
    aaa = panel.loc[panel["ticker"].eq("AAA")].iloc[0]

    assert round(aaa["revenue_growth_qoq"], 4) == 0.1000
    assert round(aaa["operating_margin_t"], 4) == 0.2000
    assert round(aaa["revenue_per_employee_t"], 4) == 10.0000
    assert round(aaa["future_revenue_growth_qoq"], 4) == 0.1000
    assert round(aaa["future_operating_margin_delta_qoq"], 4) == 0.0300
    assert round(aaa["future_revenue_per_employee_growth_qoq"], 4) == 0.0000


def test_lookahead_violation_is_detected_in_permissive_mode() -> None:
    panel = PanelBuilder(strict=False).build(
        _companies_df(),
        _scores_df(prediction_date="2025-04-01"),
        _prices_df(),
        _financials_df(),
    )

    assert len(panel) == 2
    assert panel["timing_violation"].all()
    assert panel["timing_warning"].str.contains("score_available_at").all()


def test_strict_mode_excludes_invalid_rows() -> None:
    panel = PanelBuilder(strict=True).build(
        _companies_df(),
        _scores_df(prediction_date="2025-04-01"),
        _prices_df(),
        _financials_df(),
    )

    assert panel.empty


def test_missing_data_is_handled_without_crashing() -> None:
    sparse_prices = _prices_df().loc[lambda df: df["price_date"].isin(["2025-03-31", "2025-06-30"])]
    sparse_financials = _financials_df().loc[lambda df: df["fiscal_quarter"].eq("2025Q1")]

    panel = build_analytic_panel(_companies_df(), _scores_df(), sparse_prices, sparse_financials)

    assert len(panel) == 2
    assert panel["fwd_return_1q"].isna().all()
    assert panel["future_revenue_growth_qoq"].isna().all()


def test_build_panel_cli_writes_output_and_summary(tmp_path) -> None:
    companies_path = tmp_path / "companies.csv"
    scores_path = tmp_path / "scores.csv"
    prices_path = tmp_path / "prices.csv"
    financials_path = tmp_path / "financials.csv"
    output_path = tmp_path / "analytic_panel.csv"
    _companies_df().to_csv(companies_path, index=False)
    _scores_df().to_csv(scores_path, index=False)
    _prices_df().to_csv(prices_path, index=False)
    _financials_df().to_csv(financials_path, index=False)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_panel.py",
            "--companies",
            str(companies_path),
            "--scores",
            str(scores_path),
            "--prices",
            str(prices_path),
            "--financials",
            str(financials_path),
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Analytic panel summary" in result.stdout
    assert "rows: 2" in result.stdout
    written = pd.read_csv(output_path)
    assert len(written) == 2
