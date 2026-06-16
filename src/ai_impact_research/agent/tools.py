from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_PANEL_PATH = Path("data/processed/analytic_panel.csv")
DEFAULT_BACKTEST_PATH = Path("data/processed/analysis/backtest_metrics.csv")
DEFAULT_EVIDENCE_PATH = Path("data/processed/llm_extractions_sample.jsonl")
SIGNAL_COLUMNS = [
    "ai_adoption_score",
    "ai_fluency_score",
    "ai_impact_score",
    "ai_hiring_score",
    "composite_ai_score",
    "ai_composite_score",
]
OUTCOME_COLUMNS = [
    "fwd_return_1q",
    "fwd_return_2q",
    "fwd_excess_return_1q",
    "future_revenue_growth_qoq",
    "future_operating_margin_delta_qoq",
    "future_revenue_per_employee_growth_qoq",
    "revenue_growth_qoq",
    "operating_margin_t",
    "revenue_per_employee_t",
]


def load_panel(path: str | Path = DEFAULT_PANEL_PATH) -> pd.DataFrame:
    panel_path = Path(path)
    if not panel_path.exists():
        raise FileNotFoundError(f"Panel file not found: {panel_path}")
    if panel_path.suffix.lower() == ".parquet":
        return pd.read_parquet(panel_path)
    return pd.read_csv(panel_path)


@dataclass
class CompanyReportTools:
    panel: pd.DataFrame
    backtest_path: str | Path | None = DEFAULT_BACKTEST_PATH
    evidence_path: str | Path | None = DEFAULT_EVIDENCE_PATH

    def __post_init__(self) -> None:
        self.panel = _normalize_panel(self.panel)

    def get_company_snapshot(self, ticker: str) -> dict[str, Any]:
        company = self.get_company_history(ticker)
        if company.empty:
            return {}
        return company.iloc[-1].to_dict()

    def get_company_history(self, ticker: str) -> pd.DataFrame:
        ticker_norm = _normalize_ticker(ticker)
        if "ticker" not in self.panel.columns:
            return pd.DataFrame()
        company = self.panel.loc[self.panel["ticker"].astype(str).str.upper().eq(ticker_norm)].copy()
        if company.empty:
            return pd.DataFrame()
        sort_col = _first_existing(company.columns, ["score_quarter", "quarter", "snapshot_date"])
        if sort_col:
            company = company.sort_values(sort_col)
        return company.reset_index(drop=True)

    def get_peer_comparison(self, ticker: str, peer_group: str = "sector") -> dict[str, Any]:
        snapshot = self.get_company_snapshot(ticker)
        if not snapshot:
            return {"ticker": _normalize_ticker(ticker), "peer_group": peer_group, "peers": []}
        quarter_col = _first_existing(self.panel.columns, ["score_quarter", "quarter", "snapshot_date"])
        group_value = snapshot.get(peer_group)
        peers = self.panel.copy()
        if peer_group in peers.columns:
            peers = peers.loc[peers[peer_group].eq(group_value)]
        if quarter_col:
            peers = peers.loc[peers[quarter_col].eq(snapshot.get(quarter_col))]
        cols = [
            col
            for col in ["ticker", "company_name", "name", peer_group, quarter_col, *_available_signals(peers)]
            if col and col in peers.columns
        ]
        return {
            "ticker": _normalize_ticker(ticker),
            "peer_group": peer_group,
            "peer_group_value": group_value,
            "quarter": snapshot.get(quarter_col) if quarter_col else None,
            "num_peers": int(len(peers)),
            "peers": peers[cols].sort_values("ticker").to_dict("records") if cols else [],
        }

    def get_signal_rank(self, ticker: str, signal: str) -> dict[str, Any]:
        return get_signal_rank(self.panel, ticker, signal)

    def get_latest_outcomes(self, ticker: str) -> dict[str, Any]:
        snapshot = self.get_company_snapshot(ticker)
        if not snapshot:
            return {}
        return {col: snapshot.get(col) for col in OUTCOME_COLUMNS if col in snapshot}

    def get_backtest_summary(self, signal: str) -> dict[str, Any]:
        if self.backtest_path is None:
            return {}
        path = Path(self.backtest_path)
        if not path.exists():
            return {}
        metrics = pd.read_csv(path)
        if metrics.empty:
            return {}
        if "signal" in metrics.columns and signal in set(metrics["signal"].astype(str)):
            row = metrics.loc[metrics["signal"].astype(str).eq(signal)].iloc[0]
        else:
            row = metrics.iloc[0]
        return row.to_dict()

    def get_source_evidence(self, ticker: str) -> list[dict[str, Any]]:
        if self.evidence_path is None:
            return []
        return get_source_evidence(ticker, self.evidence_path)


def get_company_snapshot(panel: pd.DataFrame, ticker: str) -> dict[str, Any]:
    return CompanyReportTools(panel).get_company_snapshot(ticker)


def get_company_history(panel: pd.DataFrame, ticker: str) -> pd.DataFrame:
    return CompanyReportTools(panel).get_company_history(ticker)


def get_peer_comparison(
    panel: pd.DataFrame,
    ticker: str,
    peer_group: str = "sector",
) -> dict[str, Any]:
    return CompanyReportTools(panel).get_peer_comparison(ticker, peer_group=peer_group)


def get_signal_rank(panel: pd.DataFrame, ticker: str, signal: str) -> dict[str, Any]:
    panel_norm = _normalize_panel(panel)
    ticker_norm = _normalize_ticker(ticker)
    if "ticker" not in panel_norm.columns:
        raise ValueError("Panel must include ticker for signal rank")
    company_rows = panel_norm.loc[panel_norm["ticker"].astype(str).str.upper().eq(ticker_norm)]
    if company_rows.empty:
        raise ValueError(f"Ticker not found in panel: {ticker_norm}")
    if signal not in panel_norm.columns:
        raise ValueError(f"Signal not found in panel: {signal}")
    quarter_col = _first_existing(panel_norm.columns, ["score_quarter", "quarter", "snapshot_date"])
    latest = company_rows.sort_values(quarter_col).iloc[-1] if quarter_col else company_rows.iloc[-1]
    sector = latest.get("sector")
    peers = panel_norm.copy()
    if "sector" in peers.columns:
        peers = peers.loc[peers["sector"].eq(sector)]
    if quarter_col:
        peers = peers.loc[peers[quarter_col].eq(latest.get(quarter_col))]
    peers = peers.dropna(subset=[signal]).copy()
    if peers.empty:
        return {
            "ticker": ticker_norm,
            "signal": signal,
            "rank": None,
            "num_peers": 0,
            "sector": sector,
            "quarter": latest.get(quarter_col) if quarter_col else None,
        }
    peers["rank_desc"] = peers[signal].rank(ascending=False, method="min")
    target = peers.loc[peers["ticker"].astype(str).str.upper().eq(ticker_norm)]
    if target.empty:
        raise ValueError(f"Ticker not found in peer rank universe: {ticker_norm}")
    return {
        "ticker": ticker_norm,
        "signal": signal,
        "rank": int(target["rank_desc"].iloc[0]),
        "num_peers": int(len(peers)),
        "sector": sector,
        "quarter": latest.get(quarter_col) if quarter_col else None,
    }


def get_latest_outcomes(panel: pd.DataFrame, ticker: str) -> dict[str, Any]:
    return CompanyReportTools(panel).get_latest_outcomes(ticker)


def get_backtest_summary(
    signal: str,
    backtest_path: str | Path = DEFAULT_BACKTEST_PATH,
) -> dict[str, Any]:
    return CompanyReportTools(pd.DataFrame(), backtest_path=backtest_path).get_backtest_summary(signal)


def get_source_evidence(
    ticker: str,
    evidence_path: str | Path = DEFAULT_EVIDENCE_PATH,
) -> list[dict[str, Any]]:
    path = Path(evidence_path)
    if not path.exists():
        return []
    ticker_norm = _normalize_ticker(ticker)
    evidence: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if _normalize_ticker(payload.get("ticker")) != ticker_norm:
                continue
            for span in payload.get("evidence", []):
                evidence.append(
                    {
                        "ticker": ticker_norm,
                        "source_document_id": payload.get("source_document_id"),
                        "source_type": payload.get("source_type"),
                        "source_date": payload.get("source_date"),
                        "text": span.get("text"),
                        "evidence_id": span.get("evidence_id"),
                    }
                )
    return evidence


def latest_company_snapshot(panel: pd.DataFrame, ticker: str) -> dict[str, Any]:
    snapshot = get_company_snapshot(panel, ticker)
    if not snapshot:
        raise ValueError(f"Ticker not found in panel: {_normalize_ticker(ticker)}")
    return snapshot


def peer_rank(
    panel: pd.DataFrame,
    ticker: str,
    score_col: str = "composite_ai_score",
) -> dict[str, Any]:
    return get_signal_rank(panel, ticker, score_col)


def _normalize_panel(panel: pd.DataFrame) -> pd.DataFrame:
    out = panel.copy()
    if "ticker" in out.columns:
        out["ticker"] = out["ticker"].astype(str).str.upper().str.strip()
    if "company_name" not in out.columns and "name" in out.columns:
        out["company_name"] = out["name"]
    if "name" not in out.columns and "company_name" in out.columns:
        out["name"] = out["company_name"]
    if "composite_ai_score" not in out.columns and "ai_composite_score" in out.columns:
        out["composite_ai_score"] = out["ai_composite_score"]
    if "ai_composite_score" not in out.columns and "composite_ai_score" in out.columns:
        out["ai_composite_score"] = out["composite_ai_score"]
    return out


def _available_signals(panel: pd.DataFrame) -> list[str]:
    return [col for col in SIGNAL_COLUMNS if col in panel.columns]


def _first_existing(columns: Any, candidates: list[str]) -> str | None:
    column_set = set(columns)
    for candidate in candidates:
        if candidate in column_set:
            return candidate
    return None


def _normalize_ticker(value: object) -> str:
    return str(value or "").strip().upper()
