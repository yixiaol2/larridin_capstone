from __future__ import annotations

import subprocess
import sys

import pandas as pd
import pytest

from ai_impact_research.ingestion.market_data import (
    MarketDataAPIClient,
    load_market_prices_csv,
    normalize_market_prices,
)


def _market_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": [" msft ", "msft", "aapl"],
            "date": ["2025-01-02", "2025-01-03", "2025-01-02"],
            "adjusted_close": [100.0, 105.0, 50.0],
            "volume": [1000, 1100, 900],
            "source_name": ["synthetic_market_sample"] * 3,
        }
    )


def test_good_market_input_passes_and_computes_returns() -> None:
    out = normalize_market_prices(_market_df())

    assert list(out["ticker"]) == ["AAPL", "MSFT", "MSFT"]
    assert out.loc[out["ticker"].eq("MSFT"), "daily_return"].iloc[0] != out.loc[
        out["ticker"].eq("MSFT"), "daily_return"
    ].iloc[0]
    assert out.loc[out["ticker"].eq("MSFT"), "daily_return"].iloc[1] == pytest.approx(0.05)
    assert "available_at" in out.columns


def test_negative_adjusted_close_fails() -> None:
    df = _market_df()
    df.loc[0, "adjusted_close"] = -1

    with pytest.raises(ValueError, match="adjusted_close"):
        normalize_market_prices(df)


def test_missing_identifier_fails() -> None:
    df = _market_df().drop(columns=["ticker"])

    with pytest.raises(ValueError, match="company_id or ticker"):
        normalize_market_prices(df)


def test_market_cli_writes_normalized_output(tmp_path) -> None:
    input_path = tmp_path / "market.csv"
    output_path = tmp_path / "market_prices_normalized.csv"
    _market_df().to_csv(input_path, index=False)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/ingest_market_data.py",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    out = pd.read_csv(output_path)

    assert "rows: 3" in result.stdout
    assert "tickers: 2" in result.stdout
    assert "daily_return" in out.columns


def test_market_api_stub_does_not_call_network() -> None:
    with pytest.raises(NotImplementedError, match="TODO"):
        MarketDataAPIClient().fetch_prices()


def test_load_market_prices_csv_accepts_price_date_alias(tmp_path) -> None:
    df = _market_df().rename(columns={"date": "price_date"})
    input_path = tmp_path / "market.csv"
    df.to_csv(input_path, index=False)

    out = load_market_prices_csv(input_path)

    assert out["price_date"].notna().all()
