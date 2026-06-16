from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ai_impact_research.agent.tools import (
    CompanyReportTools,
    get_signal_rank,
    load_panel,
)


def _panel() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "company_id": "C001",
                "company_name": "AAA Corp",
                "sector": "Software",
                "score_quarter": "2025Q1",
                "ai_adoption_score": 3,
                "composite_ai_score": 3.0,
                "fwd_return_1q": 0.02,
            },
            {
                "ticker": "AAA",
                "company_id": "C001",
                "company_name": "AAA Corp",
                "sector": "Software",
                "score_quarter": "2025Q2",
                "ai_adoption_score": 4,
                "composite_ai_score": 4.0,
                "fwd_return_1q": 0.05,
            },
            {
                "ticker": "BBB",
                "company_id": "C002",
                "company_name": "BBB Inc",
                "sector": "Software",
                "score_quarter": "2025Q2",
                "ai_adoption_score": 2,
                "composite_ai_score": 2.5,
                "fwd_return_1q": 0.01,
            },
            {
                "ticker": "CCC",
                "company_id": "C003",
                "company_name": "CCC Co",
                "sector": "Retail",
                "score_quarter": "2025Q2",
                "ai_adoption_score": 5,
                "composite_ai_score": 4.5,
                "fwd_return_1q": -0.01,
            },
        ]
    )


def test_load_panel_reads_csv(tmp_path: Path) -> None:
    path = tmp_path / "panel.csv"
    _panel().to_csv(path, index=False)

    loaded = load_panel(path)

    assert loaded.shape == (4, 8)
    assert loaded.loc[0, "ticker"] == "AAA"


def test_tool_returns_latest_company_snapshot() -> None:
    tools = CompanyReportTools(_panel())

    snapshot = tools.get_company_snapshot("aaa")

    assert snapshot["ticker"] == "AAA"
    assert snapshot["score_quarter"] == "2025Q2"
    assert snapshot["ai_adoption_score"] == 4


def test_peer_rank_calculation_works() -> None:
    tools = CompanyReportTools(_panel())

    rank = tools.get_signal_rank("AAA", "composite_ai_score")
    peers = tools.get_peer_comparison("AAA")

    assert rank["rank"] == 1
    assert rank["num_peers"] == 2
    assert peers["peer_group"] == "sector"


def test_missing_ticker_handled_gracefully() -> None:
    tools = CompanyReportTools(_panel())

    assert tools.get_company_snapshot("ZZZ") == {}
    with pytest.raises(ValueError, match="Ticker not found"):
        get_signal_rank(_panel(), "ZZZ", "composite_ai_score")


def test_get_source_evidence_reads_llm_jsonl(tmp_path: Path) -> None:
    evidence_path = tmp_path / "llm.jsonl"
    evidence_path.write_text(
        """
{"ticker":"AAA","source_document_id":"doc1","source_type":"company_web_page","source_date":"2025-01-01","extraction_created_at":"2025-01-02T00:00:00Z","model_name":"mock","prompt_version":"v1","schema_version":"s1","evidence":[{"evidence_id":"ev1","text":"AAA deployed AI assistants"}],"signal_scores":{"ai_strategy_specificity":{"score":3,"confidence":0.7,"evidence_ids":["ev1"]},"ai_operational_maturity":{"score":3,"confidence":0.7,"evidence_ids":["ev1"]},"ai_workforce_training":{"score":null,"confidence":0.0,"evidence_ids":[]},"ai_hiring_intensity":{"score":null,"confidence":0.0,"evidence_ids":[]},"ai_capex_or_infrastructure_signal":{"score":null,"confidence":0.0,"evidence_ids":[]},"ai_productivity_claim":{"score":null,"confidence":0.0,"evidence_ids":[]}},"limitations":[]}
""".strip(),
        encoding="utf-8",
    )
    tools = CompanyReportTools(_panel(), evidence_path=evidence_path)

    evidence = tools.get_source_evidence("AAA")

    assert evidence[0]["source_document_id"] == "doc1"
    assert evidence[0]["text"] == "AAA deployed AI assistants"
