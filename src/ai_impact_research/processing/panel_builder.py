from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ai_impact_research.ingestion.financials import normalize_financials
from ai_impact_research.ingestion.larridin import SCORE_COLUMNS, normalize_larridin_scores
from ai_impact_research.ingestion.market_data import normalize_market_prices
from ai_impact_research.processing.identifiers import attach_company_id, normalize_companies

PANEL_COLUMNS = [
    "company_id",
    "ticker",
    "company_name",
    "sector",
    "industry",
    "snapshot_date",
    "score_quarter",
    "score_available_at",
    "prediction_date",
    "outcome_start_date",
    "outcome_end_date",
    "quarter",
    *SCORE_COLUMNS,
    "composite_ai_score",
    "log_market_cap",
    "prior_return_1q",
    "revenue_growth_qoq",
    "operating_margin_t",
    "revenue_per_employee_t",
    "fwd_return_1q",
    "fwd_return_2q",
    "fwd_excess_return_1q",
    "future_revenue_growth_qoq",
    "future_operating_margin_delta_qoq",
    "future_revenue_per_employee_growth_qoq",
    "timing_warning",
    "timing_violation",
]


@dataclass(frozen=True)
class PanelBuilder:
    strict: bool = True

    def build(
        self,
        companies: pd.DataFrame,
        larridin_scores: pd.DataFrame,
        market_prices: pd.DataFrame,
        financial_metrics: pd.DataFrame,
    ) -> pd.DataFrame:
        companies_norm = normalize_companies(companies)
        scores = normalize_larridin_scores(larridin_scores)
        if "prediction_date" in larridin_scores.columns:
            scores["prediction_date"] = larridin_scores["prediction_date"].reset_index(drop=True)
        scores = attach_company_id(scores, companies_norm)
        prices = attach_company_id(normalize_market_prices(market_prices), companies_norm)
        financials = attach_company_id(normalize_financials(financial_metrics), companies_norm)

        scores = self._prepare_scores(scores)
        prices = self._prepare_prices(prices)
        financials = self._prepare_financials(financials)

        rows = [
            self._build_row(score, companies_norm, prices, financials)
            for score in scores.sort_values(["company_id", "snapshot_date"]).to_dict("records")
        ]
        panel = pd.DataFrame(rows)
        if panel.empty:
            return pd.DataFrame(columns=PANEL_COLUMNS)

        panel = self._add_sector_excess_return(panel)
        if self.strict:
            panel = panel.loc[~panel["timing_violation"]].copy()

        duplicates = panel.duplicated(["company_id", "score_quarter"], keep=False)
        if duplicates.any():
            keys = panel.loc[duplicates, ["company_id", "score_quarter"]].to_dict("records")
            raise ValueError(f"Analytical panel has duplicate company-quarter rows: {keys}")

        for column in PANEL_COLUMNS:
            if column not in panel.columns:
                panel[column] = pd.NA
        return panel[PANEL_COLUMNS].sort_values(["ticker", "score_quarter"]).reset_index(drop=True)

    def _prepare_scores(self, scores: pd.DataFrame) -> pd.DataFrame:
        out = scores.copy()
        out["snapshot_date"] = pd.to_datetime(out["snapshot_date"]).dt.date
        out["score_available_at"] = pd.to_datetime(out["available_at"])
        if "prediction_date" in out.columns:
            out["prediction_date"] = pd.to_datetime(out["prediction_date"]).dt.date
        else:
            out["prediction_date"] = out["score_available_at"].dt.date
        return out

    def _prepare_prices(self, prices: pd.DataFrame) -> pd.DataFrame:
        out = prices.copy()
        out["price_date"] = pd.to_datetime(out["price_date"]).dt.date
        out["available_at"] = pd.to_datetime(out["available_at"])
        return out.sort_values(["company_id", "price_date"]).reset_index(drop=True)

    def _prepare_financials(self, financials: pd.DataFrame) -> pd.DataFrame:
        out = financials.copy()
        out["fiscal_period_end"] = pd.to_datetime(out["fiscal_period_end"]).dt.date
        out["available_at"] = pd.to_datetime(out["available_at"])
        return out.sort_values(["company_id", "fiscal_period_end"]).reset_index(drop=True)

    def _build_row(
        self,
        score: dict[str, Any],
        companies: pd.DataFrame,
        prices: pd.DataFrame,
        financials: pd.DataFrame,
    ) -> dict[str, Any]:
        company_id = score["company_id"]
        prediction_date = score["prediction_date"]
        score_available_at = score["score_available_at"]
        company = self._company_record(companies, company_id)
        company_prices = prices.loc[prices["company_id"].eq(company_id)].copy()
        company_financials = financials.loc[financials["company_id"].eq(company_id)].copy()

        timing_warnings = []
        if score_available_at.date() > prediction_date:
            timing_warnings.append("score_available_at after prediction_date")

        row = {
            "company_id": company_id,
            "ticker": score.get("ticker") or company.get("ticker"),
            "company_name": score.get("company_name") or company.get("company_name") or company.get("name"),
            "sector": company.get("sector"),
            "industry": company.get("industry"),
            "snapshot_date": score["snapshot_date"],
            "score_quarter": score["score_quarter"],
            "score_available_at": score_available_at,
            "prediction_date": prediction_date,
            "quarter": score["score_quarter"],
            "timing_warning": "",
            "timing_violation": False,
        }
        for score_col in SCORE_COLUMNS:
            row[score_col] = score[score_col]
        row["composite_ai_score"] = float(np.mean([score[col] for col in SCORE_COLUMNS]))
        row["log_market_cap"] = _safe_log(company.get("market_cap"))

        row.update(self._market_features_and_outcomes(company_prices, prediction_date))
        row.update(self._financial_features_and_outcomes(company_financials, prediction_date))

        row["timing_warning"] = "; ".join(timing_warnings)
        row["timing_violation"] = bool(timing_warnings)
        return row

    def _company_record(self, companies: pd.DataFrame, company_id: str) -> dict[str, Any]:
        matches = companies.loc[companies["company_id"].eq(company_id)]
        if matches.empty:
            return {}
        return matches.iloc[0].to_dict()

    def _market_features_and_outcomes(
        self,
        prices: pd.DataFrame,
        prediction_date: Any,
    ) -> dict[str, Any]:
        if prices.empty:
            return {
                "outcome_start_date": pd.NA,
                "outcome_end_date": pd.NA,
                "prior_return_1q": pd.NA,
                "fwd_return_1q": pd.NA,
                "fwd_return_2q": pd.NA,
            }

        prior_prices = prices.loc[prices["price_date"] <= prediction_date].sort_values("price_date")
        future_prices = prices.loc[prices["price_date"] > prediction_date].sort_values("price_date")

        prior_return = pd.NA
        if len(prior_prices) >= 2:
            prior_return = _safe_return(
                prior_prices.iloc[-2]["adjusted_close"],
                prior_prices.iloc[-1]["adjusted_close"],
            )

        outcome_start_date = pd.NA
        outcome_end_date = pd.NA
        fwd_return_1q = pd.NA
        fwd_return_2q = pd.NA
        if len(future_prices) >= 2:
            start = future_prices.iloc[0]
            one_q = future_prices.iloc[1]
            outcome_start_date = start["price_date"]
            outcome_end_date = one_q["price_date"]
            fwd_return_1q = _safe_return(start["adjusted_close"], one_q["adjusted_close"])
            if len(future_prices) >= 3:
                two_q = future_prices.iloc[2]
                fwd_return_2q = _safe_return(start["adjusted_close"], two_q["adjusted_close"])

        return {
            "outcome_start_date": outcome_start_date,
            "outcome_end_date": outcome_end_date,
            "prior_return_1q": prior_return,
            "fwd_return_1q": fwd_return_1q,
            "fwd_return_2q": fwd_return_2q,
        }

    def _financial_features_and_outcomes(
        self,
        financials: pd.DataFrame,
        prediction_date: Any,
    ) -> dict[str, Any]:
        if financials.empty:
            return _empty_financial_values()

        available = financials.loc[financials["available_at"].dt.date <= prediction_date].sort_values(
            "fiscal_period_end"
        )
        future = financials.loc[financials["fiscal_period_end"] > prediction_date].sort_values(
            "fiscal_period_end"
        )

        values = _empty_financial_values()
        if not available.empty:
            current = available.iloc[-1]
            values["operating_margin_t"] = current.get("operating_margin", pd.NA)
            values["revenue_per_employee_t"] = _safe_ratio(
                current.get("revenue", pd.NA),
                current.get("employee_count", pd.NA),
            )
            if len(available) >= 2:
                previous = available.iloc[-2]
                values["revenue_growth_qoq"] = _safe_return(
                    previous.get("revenue", pd.NA),
                    current.get("revenue", pd.NA),
                )

        if len(future) >= 2:
            first = future.iloc[0]
            second = future.iloc[1]
            values["future_revenue_growth_qoq"] = _safe_return(
                first.get("revenue", pd.NA),
                second.get("revenue", pd.NA),
            )
            values["future_operating_margin_delta_qoq"] = _safe_difference(
                second.get("operating_margin", pd.NA),
                first.get("operating_margin", pd.NA),
            )
            first_rpe = _safe_ratio(first.get("revenue", pd.NA), first.get("employee_count", pd.NA))
            second_rpe = _safe_ratio(second.get("revenue", pd.NA), second.get("employee_count", pd.NA))
            values["future_revenue_per_employee_growth_qoq"] = _safe_return(first_rpe, second_rpe)

        return values

    def _add_sector_excess_return(self, panel: pd.DataFrame) -> pd.DataFrame:
        out = panel.copy()
        valid = out["fwd_return_1q"].notna()
        sector_average = out.loc[valid].groupby(["sector", "score_quarter"])["fwd_return_1q"].transform("mean")
        out.loc[valid, "fwd_excess_return_1q"] = out.loc[valid, "fwd_return_1q"] - sector_average
        return out


def build_analytic_panel(
    companies: pd.DataFrame,
    larridin_scores: pd.DataFrame,
    market_prices: pd.DataFrame,
    financials: pd.DataFrame,
    strict: bool = True,
) -> pd.DataFrame:
    return PanelBuilder(strict=strict).build(companies, larridin_scores, market_prices, financials)


def write_panel(df: pd.DataFrame, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".parquet":
        df.to_parquet(path, index=False)
    elif path.suffix.lower() == ".csv":
        df.to_csv(path, index=False)
    else:
        raise ValueError("Output path must end with .csv or .parquet")
    return path


def summarize_panel(df: pd.DataFrame) -> dict[str, Any]:
    missingness = {
        column: int(df[column].isna().sum())
        for column in [
            "fwd_return_1q",
            "fwd_return_2q",
            "future_revenue_growth_qoq",
            "prior_return_1q",
        ]
        if column in df.columns
    }
    return {
        "rows": int(len(df)),
        "companies": int(df["company_id"].dropna().nunique()) if "company_id" in df.columns else 0,
        "quarters": int(df["score_quarter"].dropna().nunique()) if "score_quarter" in df.columns else 0,
        "timing_violations": int(df["timing_violation"].sum()) if "timing_violation" in df.columns else 0,
        "missingness": missingness,
    }


def _empty_financial_values() -> dict[str, Any]:
    return {
        "revenue_growth_qoq": pd.NA,
        "operating_margin_t": pd.NA,
        "revenue_per_employee_t": pd.NA,
        "future_revenue_growth_qoq": pd.NA,
        "future_operating_margin_delta_qoq": pd.NA,
        "future_revenue_per_employee_growth_qoq": pd.NA,
    }


def _safe_log(value: Any) -> float | Any:
    if _is_missing(value):
        return pd.NA
    numeric = float(value)
    if numeric <= 0:
        return pd.NA
    return float(np.log(numeric))


def _safe_return(start: Any, end: Any) -> float | Any:
    if _is_missing(start) or _is_missing(end):
        return pd.NA
    start_float = float(start)
    if start_float == 0:
        return pd.NA
    return float(end) / start_float - 1


def _safe_ratio(numerator: Any, denominator: Any) -> float | Any:
    if _is_missing(numerator) or _is_missing(denominator):
        return pd.NA
    denominator_float = float(denominator)
    if denominator_float == 0:
        return pd.NA
    return float(numerator) / denominator_float


def _safe_difference(end: Any, start: Any) -> float | Any:
    if _is_missing(start) or _is_missing(end):
        return pd.NA
    return float(end) - float(start)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except TypeError:
        return False
