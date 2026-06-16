from __future__ import annotations

from pathlib import Path

import pandas as pd

SAMPLES_DIR = Path("data/samples")
SAMPLE_FILES = {
    "companies": SAMPLES_DIR / "companies.csv",
    "scores": SAMPLES_DIR / "larridin_scores.csv",
    "prices": SAMPLES_DIR / "market_prices.csv",
    "fundamentals": SAMPLES_DIR / "fundamentals.csv",
    "readme": SAMPLES_DIR / "README.md",
}

REQUIRED_COLUMNS = {
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

SECRET_MARKERS = ["api_key", "token", "password", "secret", "sk-", "ghp_", "xoxb-"]
SCORE_COLUMNS = [
    "ai_adoption_score",
    "ai_fluency_score",
    "ai_impact_score",
    "ai_hiring_score",
]


def _load(name: str) -> pd.DataFrame:
    return pd.read_csv(SAMPLE_FILES[name])


def test_sample_files_exist_and_are_marked_synthetic() -> None:
    for path in SAMPLE_FILES.values():
        assert path.exists(), f"Missing sample file: {path}"

    readme = SAMPLE_FILES["readme"].read_text(encoding="utf-8").lower()
    assert "synthetic" in readme

    for name in ["companies", "scores", "prices", "fundamentals"]:
        df = _load(name)
        assert "source_name" in df.columns
        assert df["source_name"].astype(str).str.lower().str.contains("synthetic").all()


def test_sample_files_have_required_columns_and_shape() -> None:
    companies = _load("companies")
    scores = _load("scores")
    prices = _load("prices")
    fundamentals = _load("fundamentals")

    for name, required in REQUIRED_COLUMNS.items():
        df = _load(name)
        assert required.issubset(df.columns), f"{name} missing {sorted(required - set(df.columns))}"

    assert 10 <= len(companies) <= 20
    assert companies["sector"].nunique() >= 4
    assert scores["ticker"].nunique() == len(companies)
    assert scores["snapshot_date"].nunique() >= 4
    assert fundamentals["fiscal_quarter"].nunique() >= 4
    assert prices["price_date"].nunique() >= scores["snapshot_date"].nunique() + 1


def test_sample_scores_and_dates_are_valid() -> None:
    scores = _load("scores")
    prices = _load("prices")
    fundamentals = _load("fundamentals")

    for col in SCORE_COLUMNS:
        assert scores[col].between(1, 5).all()

    pd.to_datetime(scores["snapshot_date"], errors="raise")
    pd.to_datetime(scores["available_at"], errors="raise")
    pd.to_datetime(prices["price_date"], errors="raise")
    pd.to_datetime(prices["available_at"], errors="raise")
    pd.to_datetime(fundamentals["fiscal_period_end"], errors="raise")
    pd.to_datetime(fundamentals["available_at"], errors="raise")


def test_sample_files_do_not_contain_credentials_or_secrets() -> None:
    for path in SAMPLE_FILES.values():
        text = path.read_text(encoding="utf-8").lower()
        assert not any(marker in text for marker in SECRET_MARKERS), path
