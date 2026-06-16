from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_impact_research.config import load_settings  # noqa: E402
from ai_impact_research.ingestion.financials import normalize_financials  # noqa: E402
from ai_impact_research.ingestion.larridin import normalize_larridin_scores  # noqa: E402
from ai_impact_research.ingestion.market_data import normalize_market_prices  # noqa: E402
from ai_impact_research.io_utils import write_csv  # noqa: E402
from ai_impact_research.processing.identifiers import normalize_companies  # noqa: E402
from ai_impact_research.processing.panel_builder import build_analytic_panel  # noqa: E402

REQUIRED_SAMPLE_COLUMNS = {
    "companies": {
        "company_id",
        "ticker",
        "name",
        "sector",
        "industry",
        "cik",
        "exchange",
        "market_cap",
        "source_name",
    },
    "scores": {
        "ticker",
        "company_name",
        "snapshot_date",
        "ai_adoption_score",
        "ai_fluency_score",
        "ai_impact_score",
        "ai_hiring_score",
        "source_name",
        "source_url",
        "available_at",
    },
    "prices": {
        "ticker",
        "price_date",
        "adjusted_close",
        "volume",
        "source_name",
        "available_at",
    },
    "fundamentals": {
        "ticker",
        "fiscal_quarter",
        "fiscal_period_end",
        "revenue",
        "gross_margin",
        "operating_margin",
        "net_income",
        "employee_count",
        "source_name",
        "available_at",
    },
}


def validate_required_columns(name: str, df: pd.DataFrame) -> None:
    required = REQUIRED_SAMPLE_COLUMNS[name]
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{name} sample data missing required columns: {sorted(missing)}")


def main() -> None:
    settings = load_settings()
    samples = settings.samples_dir
    companies = pd.read_csv(samples / "companies.csv")
    scores = pd.read_csv(samples / "larridin_scores.csv")
    prices = pd.read_csv(samples / "market_prices.csv")
    financials = pd.read_csv(samples / "fundamentals.csv")

    validate_required_columns("companies", companies)
    validate_required_columns("scores", scores)
    validate_required_columns("prices", prices)
    validate_required_columns("fundamentals", financials)

    normalized_companies = normalize_companies(companies)
    normalized_scores = normalize_larridin_scores(scores)
    normalized_prices = normalize_market_prices(prices)
    normalized_financials = normalize_financials(financials)

    panel = build_analytic_panel(companies, scores, prices, financials)
    outputs = {
        "companies": write_csv(normalized_companies, settings.processed_dir / "companies.csv"),
        "scores": write_csv(normalized_scores, settings.processed_dir / "larridin_scores.csv"),
        "prices": write_csv(normalized_prices, settings.processed_dir / "market_prices.csv"),
        "fundamentals": write_csv(normalized_financials, settings.processed_dir / "fundamentals.csv"),
        "analytic_panel": write_csv(panel, settings.processed_dir / "analytic_panel.csv"),
    }

    print(f"companies: {len(companies):,}")
    print(f"scores: {len(scores):,}")
    print(f"price rows: {len(prices):,}")
    print(f"fundamentals rows: {len(financials):,}")
    print("outputs:")
    for name, path in outputs.items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
