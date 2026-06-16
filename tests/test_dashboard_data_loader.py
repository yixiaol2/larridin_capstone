from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_impact_research.dashboard.data_loader import (
    REQUIRED_SETUP_COMMANDS,
    load_dashboard_data,
    summarize_panel,
)


def test_data_loader_reads_sample_panel(tmp_path: Path) -> None:
    panel_path = tmp_path / "analytic_panel.csv"
    pd.DataFrame(
        [
            {
                "company_id": "C001",
                "ticker": "AIVA",
                "sector": "Technology",
                "score_quarter": "2025Q1",
                "ai_adoption_score": 4,
                "fwd_return_1q": 0.05,
            },
            {
                "company_id": "C002",
                "ticker": "BRIO",
                "sector": "Retail",
                "score_quarter": "2025Q1",
                "ai_adoption_score": 2,
                "fwd_return_1q": 0.01,
            },
        ]
    ).to_csv(panel_path, index=False)

    bundle = load_dashboard_data(panel_path=panel_path, analysis_dir=tmp_path / "analysis")

    assert len(bundle.panel) == 2
    assert bundle.panel_path == panel_path
    assert "panel" not in bundle.missing_files


def test_data_loader_handles_missing_files_gracefully(tmp_path: Path) -> None:
    bundle = load_dashboard_data(panel_path=tmp_path / "missing_panel.csv", analysis_dir=tmp_path / "analysis")

    assert bundle.panel.empty
    assert "panel" in bundle.missing_files
    assert REQUIRED_SETUP_COMMANDS == [
        "python scripts/bootstrap_from_samples.py",
        "python scripts/build_panel.py",
        "python scripts/run_baseline_analysis.py",
    ]


def test_metric_summaries_compute_coverage_and_missingness() -> None:
    panel = pd.DataFrame(
        [
            {
                "company_id": "C001",
                "ticker": "AIVA",
                "sector": "Technology",
                "score_quarter": "2025Q1",
                "ai_adoption_score": 4,
                "ai_fluency_score": 4,
            },
            {
                "company_id": "C001",
                "ticker": "AIVA",
                "sector": "Technology",
                "score_quarter": "2025Q2",
                "ai_adoption_score": None,
                "ai_fluency_score": 5,
            },
            {
                "company_id": "C002",
                "ticker": "BRIO",
                "sector": "Retail",
                "score_quarter": "2025Q1",
                "ai_adoption_score": 2,
                "ai_fluency_score": None,
            },
        ]
    )

    summary = summarize_panel(panel)

    assert summary["company_count"] == 2
    assert summary["quarter_count"] == 2
    assert summary["sector_count"] == 2
    assert summary["missingness"]["ai_adoption_score"] == 1
    assert summary["missingness"]["ai_fluency_score"] == 1
