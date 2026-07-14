"""Pull the two missing regression controls: prior revenue growth (momentum)
and market cap near t0 (size).

- prior_rev_growth_yoy: YoY growth of the last fiscal quarter ENDING BEFORE t0
  (2026-01-19), from SEC companyfacts (as-first-reported). This is the growth
  investors could observe at/around t0 — the momentum control.
- mktcap_t0: shares outstanding (dei:EntityCommonStockSharesOutstanding,
  latest report before/near t0) x first close after t0 (from our cached
  prices). Fallback: yfinance fast_info market cap (current) where SEC shares
  are unavailable, flagged in `mktcap_source`.

Output: data/processed/fundamentals/controls.parquet (+.csv)

Usage:
    python scripts/pull_controls.py [--limit N]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

_UTC = dt.timezone.utc  # noqa: UP017 — py3.10 compat

T0 = dt.date(2026, 1, 19)
REV_CONCEPTS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "RevenuesNetOfInterestExpense",
]


def quarterly_series(facts: dict, concept: str) -> dict[dt.date, dict]:
    units = (facts.get("us-gaap", {}).get(concept) or {}).get("units", {})
    out: dict[dt.date, dict] = {}
    for item in units.get("USD", []):
        try:
            start = dt.date.fromisoformat(item["start"])
            end = dt.date.fromisoformat(item["end"])
        except (KeyError, ValueError):
            continue
        if not 70 <= (end - start).days <= 100:
            continue
        filed = dt.date.fromisoformat(item["filed"])
        cur = out.get(end)
        if cur is None or filed < cur["filed"]:
            out[end] = {"val": item["val"], "filed": filed}
    return out


def nearest(series: dict[dt.date, dict], target: dt.date, tol: int = 21) -> dict | None:
    best = None
    for end, rec in series.items():
        d = abs((end - target).days)
        if d <= tol and (best is None or d < best[0]):
            best = (d, rec, end)
    return {"end": best[2], **best[1]} if best else None


def shares_near_t0(facts: dict) -> float | None:
    """Latest EntityCommonStockSharesOutstanding reported on/before ~t0+45d."""
    units = (facts.get("dei", {}).get("EntityCommonStockSharesOutstanding") or {}).get("units", {})
    items = [x for v in units.values() for x in v if x.get("end")]
    cands = []
    for x in items:
        try:
            end = dt.date.fromisoformat(x["end"])
        except ValueError:
            continue
        if end <= T0 + dt.timedelta(days=45):
            cands.append((end, x.get("val")))
    if not cands:
        return None
    return max(cands)[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    load_dotenv(dotenv_path=".env")
    ua = os.environ["SEC_USER_AGENT"]

    uni = pd.read_parquet("data/processed/universe/universe.parquet")
    uni = uni[uni["cik"].notna() & uni["ticker"].notna() & ~uni["share_class_dup"]].drop_duplicates("ticker")
    if args.limit:
        uni = uni.head(args.limit)

    # entry price after t0 from cached prices
    px = pd.read_parquet("data/processed/market/prices_daily.parquet")
    after = px.loc[px.index > pd.Timestamp(T0)]
    entry = after.iloc[0] if len(after) else None

    cache_dir = Path("data/processed/fundamentals/controls_percompany")
    cache_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    n_fetched = 0
    for _, r in uni.iterrows():
        cache = cache_dir / f"{r.ticker.replace('.', '-')}.json"
        if cache.exists():
            rows.append(json.loads(cache.read_text()))
            continue
        cik = str(r["cik"]).zfill(10)
        row: dict = {"ticker": r.ticker}
        try:
            resp = requests.get(
                f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                headers={"User-Agent": ua}, timeout=60,
            )
            resp.raise_for_status()
            facts = resp.json().get("facts", {})
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL {r.ticker}: {e}")
            time.sleep(0.3)
            continue
        n_fetched += 1
        time.sleep(0.12)

        rev = {}
        for concept in REV_CONCEPTS:
            rev = quarterly_series(facts, concept)
            if len(rev) >= 4:
                break
        # last quarter ending BEFORE t0 (momentum window)
        prior_end = None
        for end in sorted(rev, reverse=True):
            if end < T0:
                prior_end = end
                break
        if prior_end is not None:
            q = rev[prior_end]
            yoy = nearest(rev, prior_end - dt.timedelta(days=365))
            if yoy and yoy["val"]:
                row["prior_rev_growth_yoy"] = q["val"] / yoy["val"] - 1
                row["prior_q_end"] = str(prior_end)

        shares = shares_near_t0(facts)
        yf_ticker = r.ticker.replace(".", "-")
        price0 = float(entry[yf_ticker]) if entry is not None and yf_ticker in entry.index and pd.notna(entry[yf_ticker]) else None
        if shares and price0:
            row["mktcap_t0"] = shares * price0
            row["mktcap_source"] = "sec_shares_x_jan_price"
        cache.write_text(json.dumps(row))
        rows.append(row)
        if n_fetched % 50 == 0:
            print(f"  fetched {n_fetched}")

    df = pd.DataFrame(rows)

    # yfinance fallback for missing mktcap
    missing = df[df.get("mktcap_t0").isna()]["ticker"].tolist() if "mktcap_t0" in df.columns else df["ticker"].tolist()
    if missing:
        import yfinance as yf
        print(f"yfinance fallback for {len(missing)} tickers...")
        for t in missing:
            try:
                mc = yf.Ticker(t.replace(".", "-")).fast_info.get("marketCap")
                if mc:
                    df.loc[df["ticker"] == t, "mktcap_t0"] = mc
                    df.loc[df["ticker"] == t, "mktcap_source"] = "yfinance_current"
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.1)

    out = Path("data/processed/fundamentals")
    df.to_parquet(out / "controls.parquet", index=False)
    df.to_csv(out / "controls.csv", index=False)
    print(f"\ncompanies: {len(df)}")
    for c in ["prior_rev_growth_yoy", "mktcap_t0"]:
        if c in df.columns:
            print(f"  {c}: non-null {df[c].notna().sum()}")
    if "mktcap_source" in df.columns:
        print(df["mktcap_source"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
