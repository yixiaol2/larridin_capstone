from __future__ import annotations

from typing import Any, Protocol

import pandas as pd

from ai_impact_research.agent.tools import (
    OUTCOME_COLUMNS,
    SIGNAL_COLUMNS,
    CompanyReportTools,
)


class CompanyReportLLMClient(Protocol):
    def rewrite_report(self, context: dict[str, Any], draft_report: str) -> str:
        ...


def generate_company_report(
    panel: pd.DataFrame | CompanyReportTools,
    ticker: str,
    *,
    use_llm: bool = False,
    llm_client: CompanyReportLLMClient | None = None,
    signal: str = "composite_ai_score",
) -> str:
    tools = panel if isinstance(panel, CompanyReportTools) else CompanyReportTools(panel)
    context = build_report_context(tools, ticker, signal=signal)
    draft = render_templated_report(context)
    if use_llm:
        if llm_client is None:
            return draft + "\n\nLLM narrative generation was requested but no LLM client was provided."
        rewritten = llm_client.rewrite_report(context, draft)
        return _enforce_disclaimer(rewritten)
    return draft


def build_report_context(
    tools: CompanyReportTools,
    ticker: str,
    *,
    signal: str = "composite_ai_score",
) -> dict[str, Any]:
    snapshot = tools.get_company_snapshot(ticker)
    if not snapshot:
        return {"ticker": ticker.upper(), "snapshot": {}, "missing": True}
    history = tools.get_company_history(ticker)
    signal_rank = tools.get_signal_rank(ticker, _resolve_signal(snapshot, signal))
    return {
        "ticker": ticker.upper(),
        "snapshot": snapshot,
        "history": _records(history),
        "peer_comparison": tools.get_peer_comparison(ticker),
        "signal_rank": signal_rank,
        "latest_outcomes": tools.get_latest_outcomes(ticker),
        "backtest_summary": tools.get_backtest_summary(signal_rank["signal"]),
        "source_evidence": tools.get_source_evidence(ticker),
        "missing": False,
    }


def render_templated_report(context: dict[str, Any]) -> str:
    ticker = context["ticker"]
    if context.get("missing"):
        return _missing_report(ticker)

    snapshot = context["snapshot"]
    name = snapshot.get("company_name") or snapshot.get("name") or ticker
    latest_quarter = snapshot.get("score_quarter") or snapshot.get("quarter") or "unavailable"
    rank = context.get("signal_rank", {})
    outcomes = context.get("latest_outcomes", {})
    backtest = context.get("backtest_summary", {})
    evidence = context.get("source_evidence", [])

    return _enforce_disclaimer(
        f"""# {name} ({ticker}) Research Report

## Executive summary

{name} is included in the analytical panel for {latest_quarter}. The latest available AI signal profile and future outcome fields are summarized below. This report is generated from deterministic local data tools; it does not establish causality and does not use external sources.

## AI signal profile

{_score_bullets(snapshot)}

## Peer comparison

{_peer_text(rank)}

## Historical performance context

{_history_text(context.get("history", []))}

## Signal-to-outcome research context

{_outcome_text(outcomes)}

{_backtest_text(backtest)}

## Evidence excerpts

{_evidence_text(evidence)}

## Caveats and limitations

- Data is unavailable where fields are missing from the processed analytical panel.
- Signals and outcomes are observational research features, not causal proof.
- Synthetic sample data is for reproducibility checks only and must not be interpreted as real company performance.
- LLM-generated narrative, when enabled, may only rewrite the provided context and must not add facts.

## Non-investment-advice disclaimer

This report is for research and educational use only. It is not investment advice, not a recommendation to buy or sell securities, and not evidence that AI adoption determines future performance.
"""
    )


def _missing_report(ticker: str) -> str:
    return _enforce_disclaimer(
        f"""# {ticker} Research Report

## Executive summary

Data is unavailable for ticker {ticker}. The ticker was not found in the analytical panel.

## AI signal profile

Data is unavailable.

## Peer comparison

Data is unavailable.

## Historical performance context

Data is unavailable.

## Signal-to-outcome research context

Data is unavailable.

## Evidence excerpts

Data is unavailable.

## Caveats and limitations

- The requested ticker is missing from the provided panel.
- No unsupported conclusions are generated for missing data.

## Non-investment-advice disclaimer

This report is for research and educational use only. It is not investment advice and does not establish causality.
"""
    )


def _score_bullets(snapshot: dict[str, Any]) -> str:
    lines = []
    for col in SIGNAL_COLUMNS:
        if col in snapshot:
            lines.append(f"- {col}: {_fmt(snapshot.get(col))}")
    return "\n".join(lines) if lines else "Data is unavailable."


def _peer_text(rank: dict[str, Any]) -> str:
    if not rank or rank.get("rank") is None:
        return "Data is unavailable."
    return (
        f"For {rank.get('quarter', 'unavailable')}, the company ranks "
        f"{rank.get('rank')} of {rank.get('num_peers')} sector peers on {rank.get('signal')}."
    )


def _history_text(history: list[dict[str, Any]]) -> str:
    if not history:
        return "Data is unavailable."
    first = history[0]
    last = history[-1]
    start = first.get("score_quarter") or first.get("quarter") or "first observed period"
    end = last.get("score_quarter") or last.get("quarter") or "latest observed period"
    return (
        f"The panel includes {len(history)} observed row(s) from {start} through {end}. "
        "Use the dashboard for detailed quarter-by-quarter charts."
    )


def _outcome_text(outcomes: dict[str, Any]) -> str:
    available = [(col, outcomes.get(col)) for col in OUTCOME_COLUMNS if col in outcomes]
    if not available:
        return "Latest outcome data is unavailable."
    return "Latest available outcome fields:\n\n" + "\n".join(
        f"- {col}: {_fmt(value)}" for col, value in available
    )


def _backtest_text(backtest: dict[str, Any]) -> str:
    if not backtest:
        return "\nBacktest summary is unavailable."
    fields = [
        "signal",
        "outcome",
        "cumulative_return",
        "sharpe_ratio",
        "max_drawdown",
        "number_of_rebalances",
    ]
    lines = [f"- {field}: {_fmt(backtest.get(field))}" for field in fields if field in backtest]
    return "\nBacktest context for the selected signal:\n\n" + "\n".join(lines)


def _evidence_text(evidence: list[dict[str, Any]]) -> str:
    if not evidence:
        return "Evidence excerpts are unavailable."
    return "\n".join(
        f"- {item.get('source_document_id', 'unknown source')}: {item.get('text', 'unavailable')}"
        for item in evidence[:5]
    )


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    return df.where(pd.notna(df), None).to_dict("records")


def _resolve_signal(snapshot: dict[str, Any], signal: str) -> str:
    if signal in snapshot:
        return signal
    if signal == "composite_ai_score" and "ai_composite_score" in snapshot:
        return "ai_composite_score"
    if signal == "ai_composite_score" and "composite_ai_score" in snapshot:
        return "composite_ai_score"
    return signal


def _fmt(value: object, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return "unavailable"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _enforce_disclaimer(report: str) -> str:
    lower = report.lower()
    additions = []
    if "not investment advice" not in lower:
        additions.append("This report is not investment advice.")
    if "does not establish causality" not in lower:
        additions.append("This report does not establish causality.")
    if not additions:
        return report
    return report.rstrip() + "\n\n" + " ".join(additions) + "\n"
