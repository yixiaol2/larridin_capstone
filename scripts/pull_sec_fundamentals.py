"""Pull post-t0 quarterly fundamentals (outcome variables) from SEC companyfacts.

For each company: the first fiscal quarter ENDING after t0 (2026-01-19) that
has been reported, plus its prior quarter and year-ago quarter for growth
calculations. Values are taken from the earliest filing that reported them
(as-first-reported; avoids restatement look-ahead). Also pulls employee count
(dei:EntityNumberOfEmployees, annual) as the hiring-signal denominator.

Free SEC API (declared User-Agent), ~10 req/s allowed. Idempotent via
per-ticker JSON cache of extracted series (not the multi-MB raw responses).

Output: data/processed/fundamentals/q1_outcomes.parquet (+.csv)

Usage:
    python scripts/pull_sec_fundamentals.py [--limit N]
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

T0 = dt.date(2026, 1, 19)
REV_CONCEPTS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "RevenuesNetOfInterestExpense",  # banks/insurers
]


def quarterly_series(facts: dict, concept: str) -> dict[dt.date, dict]:
    """end_date -> {val, filed} for ~quarterly (70-100 day) USD periods,
    keeping the EARLIEST filing per period (as-first-reported)."""
    units = (facts.get("us-gaap", {}).get(concept) or {}).get("units", {})
    out: dict[dt.date, dict] = {}
    for item in units.get("USD", []):
        try:
            start = dt.date.fromisoformat(item["start"])
            end = dt.date.fromisoformat(item["end"])
        except (KeyError, ValueError):
            continue
        span = (end - start).days
        if not 70 <= span <= 100:
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

    cache_dir = Path("data/processed/fundamentals/percompany")
    cache_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    n_fetched = 0
    for _, r in uni.iterrows():
        cache = cache_dir / f"{r.ticker.replace('.', '-')}.json"
        if cache.exists():
            rows.append(json.loads(cache.read_text()))
            continue
        cik = str(r["cik"]).zfill(10)
        try:
            resp = requests.get(
                f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                headers={"User-Agent": ua},
                timeout=60,
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
        op = quarterly_series(facts, "OperatingIncomeLoss")

        # first reported fiscal quarter ending after t0
        target = None
        for end in sorted(rev):
            if end > T0:
                target = end
                break
        row: dict = {"ticker": r.ticker, "cik": cik}
        if target is not None:
            q = rev[target]
            prev = nearest(rev, target - dt.timedelta(days=91))
            yoy = nearest(rev, target - dt.timedelta(days=365))
            row.update(
                q_end=str(target), rev_q=q["val"], rev_filed=str(q["filed"]),
                rev_prev=(prev or {}).get("val"), rev_yoy=(yoy or {}).get("val"),
            )
            oq, oprev, oyoy = nearest(op, target, 5), nearest(op, target - dt.timedelta(days=91)), nearest(op, target - dt.timedelta(days=365))
            if oq and q["val"]:
                row["op_margin_q"] = oq["val"] / q["val"]
                if oprev and (prev or {}).get("val"):
                    row["op_margin_delta_qoq"] = row["op_margin_q"] - oprev["val"] / prev["val"]
                if oyoy and (yoy or {}).get("val"):
                    row["op_margin_delta_yoy"] = row["op_margin_q"] - oyoy["val"] / yoy["val"]

        # employees: latest annual value (any vintage; scale denominator)
        emp = (facts.get("dei", {}).get("EntityNumberOfEmployees") or {}).get("units", {})
        emp_items = [x for v in emp.values() for x in v]
        if emp_items:
            latest = max(emp_items, key=lambda x: x.get("end", ""))
            row["employees"] = latest.get("val")
            row["employees_asof"] = latest.get("end")

        cache.write_text(json.dumps(row))
        rows.append(row)
        if n_fetched % 50 == 0:
            print(f"  fetched {n_fetched}")

    df = pd.DataFrame(rows)
    if "rev_q" in df.columns:
        df["rev_growth_qoq"] = df["rev_q"] / df["rev_prev"] - 1
        df["rev_growth_yoy"] = df["rev_q"] / df["rev_yoy"] - 1
    out = Path("data/processed/fundamentals")
    df.to_parquet(out / "q1_outcomes.parquet", index=False)
    df.to_csv(out / "q1_outcomes.csv", index=False)

    print(f"\ncompanies: {len(df)}")
    for c in ["rev_q", "rev_growth_qoq", "rev_growth_yoy", "op_margin_q", "op_margin_delta_yoy", "employees"]:
        if c in df.columns:
            print(f"  {c:>20s}: non-null {df[c].notna().sum()}")
    print(f"\noutput -> {out / 'q1_outcomes.parquet'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
