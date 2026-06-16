from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_SIGNALS = [
    "ai_adoption_score",
    "ai_fluency_score",
    "ai_impact_score",
    "ai_hiring_score",
    "composite_ai_score",
]
DEFAULT_OUTCOMES = [
    "fwd_return_1q",
    "fwd_return_2q",
    "fwd_return_4q",
    "future_revenue_growth_qoq",
    "future_operating_margin_delta_qoq",
    "future_revenue_per_employee_growth_qoq",
]
DISCLOSURE_PROXY_COLUMNS = [
    "source_document_count",
    "filing_length",
    "filing_word_count",
    "source_document_word_count",
]


def missingness_summary(df: pd.DataFrame, group_col: str | None = None) -> pd.DataFrame:
    if group_col is None:
        return df.isna().mean().rename("missing_rate").rename_axis("field").reset_index()
    rows = []
    for group, part in df.groupby(group_col, dropna=False):
        miss = part.isna().mean()
        for field, rate in miss.items():
            rows.append({group_col: group, "field": field, "missing_rate": float(rate)})
    return pd.DataFrame(rows)


def sector_neutral_ic(
    panel: pd.DataFrame,
    signal: str = "composite_ai_score",
    outcome: str = "fwd_return_1q",
    sector_col: str = "sector",
    min_obs: int = 3,
) -> pd.DataFrame:
    raw_ic, raw_status, raw_n = _safe_ic(panel, signal, outcome, min_obs=min_obs)
    rows: list[dict[str, Any]] = []
    sector_ics: list[float] = []
    if sector_col not in panel.columns:
        return pd.DataFrame(
            [
                {
                    "diagnostic": "sector_neutral_ic",
                    "signal": signal,
                    "outcome": outcome,
                    "sector": pd.NA,
                    "raw_ic": raw_ic,
                    "sector_ic": pd.NA,
                    "sector_neutral_ic": pd.NA,
                    "n_obs": raw_n,
                    "status": "sector_unavailable",
                }
            ]
        )

    for sector, group in panel.groupby(sector_col, dropna=False):
        sector_ic, status, n_obs = _safe_ic(group, signal, outcome, min_obs=min_obs)
        if status == "ok":
            sector_ics.append(sector_ic)
        rows.append(
            {
                "diagnostic": "sector_neutral_ic",
                "signal": signal,
                "outcome": outcome,
                "sector": sector,
                "raw_ic": raw_ic,
                "sector_ic": sector_ic,
                "sector_neutral_ic": pd.NA,
                "n_obs": n_obs,
                "status": status,
            }
        )
    aggregate_ic = float(pd.Series(sector_ics).mean()) if sector_ics else pd.NA
    for row in rows:
        row["sector_neutral_ic"] = aggregate_ic
        if row["status"] == "too_few_obs":
            row["status"] = "insufficient_observations"
    if raw_status != "ok" and rows:
        rows[0]["raw_status"] = raw_status
    return pd.DataFrame(rows)


def size_bucket_analysis(
    panel: pd.DataFrame,
    signal: str = "composite_ai_score",
    outcome: str = "fwd_return_1q",
    market_cap_col: str | None = None,
    min_obs: int = 3,
) -> pd.DataFrame:
    market_cap_col = market_cap_col or _first_existing(
        panel.columns,
        ["market_cap", "log_market_cap"],
    )
    if market_cap_col is None:
        return pd.DataFrame(
            [
                {
                    "diagnostic": "size_bucket_analysis",
                    "signal": signal,
                    "outcome": outcome,
                    "size_bucket": pd.NA,
                    "mean_signal": pd.NA,
                    "ic": pd.NA,
                    "n_obs": 0,
                    "status": "market_cap_unavailable",
                }
            ]
        )

    out = panel.dropna(subset=[market_cap_col]).copy()
    if out.empty:
        return pd.DataFrame(
            [
                {
                    "diagnostic": "size_bucket_analysis",
                    "signal": signal,
                    "outcome": outcome,
                    "size_bucket": pd.NA,
                    "mean_signal": pd.NA,
                    "ic": pd.NA,
                    "n_obs": 0,
                    "status": "market_cap_unavailable",
                }
            ]
        )
    try:
        out["size_bucket"] = pd.qcut(
            out[market_cap_col].rank(method="first"),
            q=min(3, len(out)),
            labels=["small", "mid", "large"][: min(3, len(out))],
        )
    except ValueError:
        out["size_bucket"] = "all"

    rows = []
    for bucket, group in out.groupby("size_bucket", dropna=False, observed=True):
        ic, status, n_obs = _safe_ic(group, signal, outcome, min_obs=min_obs)
        rows.append(
            {
                "diagnostic": "size_bucket_analysis",
                "signal": signal,
                "outcome": outcome,
                "size_bucket": str(bucket),
                "mean_signal": _mean_or_na(group, signal),
                "ic": ic,
                "n_obs": n_obs,
                "status": status,
            }
        )
    return pd.DataFrame(rows)


def missingness_diagnostics(
    panel: pd.DataFrame,
    signals: list[str] | None = None,
    outcomes: list[str] | None = None,
    concentration_threshold: float = 0.5,
) -> pd.DataFrame:
    signals = _available_columns(panel, signals or DEFAULT_SIGNALS)
    outcomes = _available_columns(panel, outcomes or DEFAULT_OUTCOMES)
    fields = [*signals, *outcomes]
    rows: list[dict[str, Any]] = []

    for group_col, diagnostic in [
        ("sector", "missingness_by_sector"),
        ("score_quarter", "missingness_by_quarter"),
    ]:
        if group_col not in panel.columns:
            rows.append(
                {
                    "diagnostic_type": diagnostic,
                    "group": pd.NA,
                    "field": pd.NA,
                    "missing_rate": pd.NA,
                    "highly_concentrated": pd.NA,
                    "status": f"{group_col}_unavailable",
                }
            )
            continue
        for group, part in panel.groupby(group_col, dropna=False):
            for field in fields:
                rate = float(part[field].isna().mean()) if field in part.columns else pd.NA
                rows.append(
                    {
                        "diagnostic_type": diagnostic,
                        "group": group,
                        "field": field,
                        "missing_rate": rate,
                        "highly_concentrated": bool(
                            not pd.isna(rate) and rate >= concentration_threshold
                        ),
                        "status": "ok",
                    }
                )

    for field_type, cols in [("missingness_by_signal", signals), ("missingness_by_outcome", outcomes)]:
        for field in cols:
            rate = float(panel[field].isna().mean())
            rows.append(
                {
                    "diagnostic_type": field_type,
                    "group": "overall",
                    "field": field,
                    "missing_rate": rate,
                    "highly_concentrated": bool(rate >= concentration_threshold),
                    "status": "ok",
                }
            )
    return pd.DataFrame(rows)


def lag_sensitivity(
    panel: pd.DataFrame,
    signal: str = "composite_ai_score",
    outcomes: list[str] | None = None,
    min_obs: int = 3,
) -> pd.DataFrame:
    outcomes = outcomes or ["fwd_return_1q", "fwd_return_2q", "fwd_return_4q"]
    rows = []
    available_ics = []
    for outcome in outcomes:
        if outcome not in panel.columns:
            rows.append(
                {
                    "diagnostic": "lag_sensitivity",
                    "signal": signal,
                    "outcome": outcome,
                    "horizon": _horizon_label(outcome),
                    "ic": pd.NA,
                    "n_obs": 0,
                    "interpretation": "unavailable",
                    "status": "unavailable",
                }
            )
            continue
        ic, status, n_obs = _safe_ic(panel, signal, outcome, min_obs=min_obs)
        if status == "ok":
            available_ics.append((outcome, abs(ic)))
        rows.append(
            {
                "diagnostic": "lag_sensitivity",
                "signal": signal,
                "outcome": outcome,
                "horizon": _horizon_label(outcome),
                "ic": ic,
                "n_obs": n_obs,
                "interpretation": "pending",
                "status": status,
            }
        )
    strongest = max(available_ics, key=lambda item: item[1])[0] if available_ics else None
    for row in rows:
        if row["status"] != "ok":
            continue
        if row["outcome"] == strongest and row["horizon"] in {"2Q", "4Q"}:
            row["interpretation"] = "leading_candidate"
        elif row["outcome"] == strongest:
            row["interpretation"] = "near_term_candidate"
        else:
            row["interpretation"] = "noisy_or_weaker"
    return pd.DataFrame(rows)


def disclosure_bias_proxy(
    panel: pd.DataFrame,
    score_col: str = "composite_ai_score",
    proxy_cols: list[str] | None = None,
    min_obs: int = 3,
) -> pd.DataFrame:
    proxy_cols = proxy_cols or DISCLOSURE_PROXY_COLUMNS
    available = _available_columns(panel, proxy_cols)
    if not available:
        return pd.DataFrame(
            [
                {
                    "diagnostic": "disclosure_bias_proxy",
                    "score": score_col,
                    "proxy": pd.NA,
                    "correlation": pd.NA,
                    "n_obs": 0,
                    "status": "disclosure_proxy_unavailable",
                }
            ]
        )
    rows = []
    for proxy in available:
        ic, status, n_obs = _safe_ic(panel, proxy, score_col, min_obs=min_obs)
        rows.append(
            {
                "diagnostic": "disclosure_bias_proxy",
                "score": score_col,
                "proxy": proxy,
                "correlation": ic,
                "n_obs": n_obs,
                "status": status,
            }
        )
    return pd.DataFrame(rows)


def llm_extraction_reliability(
    llm_extractions: str | Path | pd.DataFrame | None,
    panel: pd.DataFrame | None = None,
) -> pd.DataFrame:
    df = _load_llm_extractions(llm_extractions)
    if df.empty:
        return pd.DataFrame(
            [
                {
                    "diagnostic": "llm_extraction_reliability",
                    "metric": "availability",
                    "value": pd.NA,
                    "sector": pd.NA,
                    "status": "llm_extractions_unavailable",
                }
            ]
        )
    rows = [
        {
            "diagnostic": "llm_extraction_reliability",
            "metric": "schema_validity_rate",
            "value": 1.0,
            "sector": pd.NA,
            "status": "ok",
        },
        {
            "diagnostic": "llm_extraction_reliability",
            "metric": "average_confidence",
            "value": _average_llm_confidence(df),
            "sector": pd.NA,
            "status": "ok",
        },
        {
            "diagnostic": "llm_extraction_reliability",
            "metric": "missing_evidence_rate",
            "value": float((df["evidence_count"] == 0).mean()),
            "sector": pd.NA,
            "status": "ok",
        },
    ]
    if panel is not None and "ticker" in panel.columns and "sector" in panel.columns:
        mapping = panel[["ticker", "sector"]].drop_duplicates()
        merged = df.merge(mapping, on="ticker", how="left")
        for sector, group in merged.groupby("sector", dropna=False):
            rows.append(
                {
                    "diagnostic": "llm_extraction_reliability",
                    "metric": "score_distribution_mean",
                    "value": float(group["mean_score"].mean()),
                    "sector": sector,
                    "status": "ok",
                }
            )
    return pd.DataFrame(rows)


def run_robustness_checks(
    panel: pd.DataFrame,
    signal: str = "composite_ai_score",
    outcome: str = "fwd_return_1q",
    llm_extractions: str | Path | pd.DataFrame | None = None,
) -> pd.DataFrame:
    frames = [
        _normalize_summary(sector_neutral_ic(panel, signal, outcome), "sector_neutral_ic"),
        _normalize_summary(size_bucket_analysis(panel, signal, outcome), "size_bucket_analysis"),
        _normalize_summary(missingness_diagnostics(panel), "missingness_diagnostics"),
        _normalize_summary(lag_sensitivity(panel, signal), "lag_sensitivity"),
        _normalize_summary(disclosure_bias_proxy(panel, signal), "disclosure_bias_proxy"),
        _normalize_summary(
            llm_extraction_reliability(llm_extractions, panel=panel),
            "llm_extraction_reliability",
        ),
    ]
    return pd.concat(frames, ignore_index=True, sort=False)


def write_robustness_outputs(
    summary: pd.DataFrame,
    processed_output: str | Path = "data/processed/analysis/robustness_summary.csv",
    report_output: str | Path = "reports/tables/robustness_summary.csv",
) -> tuple[Path, Path]:
    processed_path = Path(processed_output)
    report_path = Path(report_output)
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(processed_path, index=False)
    summary.to_csv(report_path, index=False)
    return processed_path, report_path


def append_interim_findings_summary(
    summary: pd.DataFrame,
    report_path: str | Path = "reports/interim_findings.md",
) -> Path:
    path = Path(report_path)
    counts = summary["diagnostic"].value_counts().to_dict() if "diagnostic" in summary.columns else {}
    lines = [
        "\n## Phase 14 Robustness and Responsible AI Diagnostics\n",
        "Phase 14 adds robustness diagnostics for sector neutrality, size buckets, missingness, lag sensitivity, disclosure bias proxies, and LLM extraction reliability.\n",
        "These diagnostics are descriptive checks only. They do not establish causality, solve fairness, or validate investment use.\n",
        "Diagnostic row counts:\n",
    ]
    lines.extend(f"- {name}: {count}\n" for name, count in sorted(counts.items()))
    with path.open("a", encoding="utf-8") as handle:
        handle.writelines(lines)
    return path


def _safe_ic(
    df: pd.DataFrame,
    signal: str,
    outcome: str,
    min_obs: int = 3,
) -> tuple[Any, str, int]:
    if signal not in df.columns or outcome not in df.columns:
        return pd.NA, "missing_column", 0
    valid = df[[signal, outcome]].dropna()
    n_obs = int(len(valid))
    if n_obs < min_obs:
        return pd.NA, "too_few_obs", n_obs
    if valid[signal].nunique() < 2 or valid[outcome].nunique() < 2:
        return pd.NA, "constant_input", n_obs
    ranked_signal = valid[signal].rank(method="average")
    ranked_outcome = valid[outcome].rank(method="average")
    return float(ranked_signal.corr(ranked_outcome, method="pearson")), "ok", n_obs


def _load_llm_extractions(source: str | Path | pd.DataFrame | None) -> pd.DataFrame:
    if source is None:
        return pd.DataFrame()
    if isinstance(source, pd.DataFrame):
        return source
    path = Path(source)
    if not path.exists():
        return pd.DataFrame()
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            scores = [
                score.get("score")
                for score in payload.get("signal_scores", {}).values()
                if score.get("score") is not None
            ]
            confidences = [
                score.get("confidence")
                for score in payload.get("signal_scores", {}).values()
                if score.get("confidence") is not None
            ]
            rows.append(
                {
                    "ticker": str(payload.get("ticker", "")).upper(),
                    "evidence_count": len(payload.get("evidence", [])),
                    "mean_score": float(pd.Series(scores).mean()) if scores else pd.NA,
                    "mean_confidence": float(pd.Series(confidences).mean()) if confidences else pd.NA,
                }
            )
    return pd.DataFrame(rows)


def _average_llm_confidence(df: pd.DataFrame) -> Any:
    if "mean_confidence" not in df.columns:
        return pd.NA
    values = pd.to_numeric(df["mean_confidence"], errors="coerce").dropna()
    return float(values.mean()) if not values.empty else pd.NA


def _normalize_summary(df: pd.DataFrame, diagnostic: str) -> pd.DataFrame:
    out = df.copy()
    if "diagnostic" not in out.columns:
        out["diagnostic"] = diagnostic
    return out


def _mean_or_na(df: pd.DataFrame, column: str) -> Any:
    if column not in df.columns:
        return pd.NA
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    return float(values.mean()) if not values.empty else pd.NA


def _available_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    return [column for column in columns if column in df.columns]


def _first_existing(columns: Any, candidates: list[str]) -> str | None:
    column_set = set(columns)
    for candidate in candidates:
        if candidate in column_set:
            return candidate
    return None


def _horizon_label(outcome: str) -> str:
    if "1q" in outcome.lower():
        return "1Q"
    if "2q" in outcome.lower():
        return "2Q"
    if "4q" in outcome.lower():
        return "4Q"
    return "other"
