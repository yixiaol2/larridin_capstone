"""Pull daily prices for the study universe and compute forward returns from t0.

t0 = 2026-01-19 (Larridin aiScores assessedAt). Point-in-time discipline:
entry price is the first trading close strictly AFTER t0; horizon returns use
the last available close on or before t0 + h months. Tickers with no price
data, or whose series stops mid-window (delisted/acquired during the period),
are reported — not silently dropped.

Input:  data/processed/universe/universe.parquet
Output: data/processed/market/prices_daily.parquet
        data/processed/market/forward_returns.parquet (+.csv)
        data/processed/market/price_coverage_report.csv

Usage:
    python scripts/pull_prices_returns.py
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import yfinance as yf

T0 = pd.Timestamp("2026-01-19")
HORIZONS_MONTHS = [1, 2, 3, 4]
START = "2026-01-02"


def main() -> int:
    out_dir = Path("data/processed/market")
    out_dir.mkdir(parents=True, exist_ok=True)

    uni = pd.read_parquet("data/processed/universe/universe.parquet")
    rows = uni[uni["ticker"].notna()].drop_duplicates("ticker")
    # Yahoo uses '-' where exchanges use '.' (BRK.B -> BRK-B).
    tickers = sorted(rows["ticker"].str.replace(".", "-", regex=False))
    print(f"pulling {len(tickers)} tickers from {START} ...")

    px = yf.download(tickers, start=START, auto_adjust=True, progress=False)["Close"]
    px = px.dropna(axis=1, how="all")
    px.to_parquet(out_dir / "prices_daily.parquet")
    print(f"got data for {px.shape[1]}/{len(tickers)} tickers, {px.shape[0]} trading days, last day {px.index[-1].date()}")

    # entry: first close strictly after t0
    after_t0 = px.loc[px.index > T0]
    entry_date = after_t0.index[0]
    entry = after_t0.iloc[0]

    res = pd.DataFrame({"ticker_yf": px.columns, "entry_price": entry})
    res["entry_date"] = entry_date
    for h in HORIZONS_MONTHS:
        target = T0 + pd.DateOffset(months=h)
        upto = px.loc[px.index <= target]
        res[f"fwd_ret_{h}m"] = upto.iloc[-1] / entry - 1 if len(upto) else pd.NA
    res["fwd_ret_latest"] = px.iloc[-1] / entry - 1
    res["last_price_date"] = px.apply(lambda s: s.last_valid_index())

    # coverage report
    stale_cutoff = px.index[-1] - pd.Timedelta(days=10)
    missing = sorted(set(tickers) - set(px.columns))
    stalled = res[res["last_price_date"] < stale_cutoff]
    cov = pd.DataFrame(
        [{"issue": "no_data", "ticker": t} for t in missing]
        + [
            {"issue": f"stops_{r.last_price_date.date()}", "ticker": r.ticker_yf}
            for r in stalled.itertuples()
        ]
    )
    cov.to_csv(out_dir / "price_coverage_report.csv", index=False)

    res["ticker"] = res["ticker_yf"].str.replace("-", ".", regex=False)
    res = res.reset_index(drop=True)
    res.to_parquet(out_dir / "forward_returns.parquet", index=False)
    res.to_csv(out_dir / "forward_returns.csv", index=False)

    print(f"entry date: {entry_date.date()}")
    print(f"no data: {len(missing)} -> {missing}")
    print(f"stops mid-window: {len(stalled)} -> {stalled['ticker_yf'].tolist()}")
    print(f"\nforward return summary:\n{res[[f'fwd_ret_{h}m' for h in HORIZONS_MONTHS] + ['fwd_ret_latest']].describe().round(3)}")
    print(f"\noutputs -> {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
