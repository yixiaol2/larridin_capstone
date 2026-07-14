"""Collect the monthly hiring snapshot for the full universe via Exa search.

Per company: one neural search for AI-related job postings in the trailing
~30-day window, numResults=25 with highlights (highlights add no cost on the
current plan). Companies whose results saturate (>=25 returned) get one deeper
follow-up at numResults=75, while budget allows.

Safety: hard abort once cumulative Exa cost exceeds --budget-cap (default
$15.50). Idempotent: existing per-ticker files are skipped, so the script can
resume after any failure.

Raw output: data/raw/exa/<snapshot>/jobs_{ticker}.json + _manifest.json
(classification happens in a separate step).

Usage:
    python scripts/collect_hiring_exa.py --snapshot 2026-06 [--limit N]
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

_UTC = dt.timezone.utc  # noqa: UP017 — py3.10 compat (datetime.UTC needs 3.11)

AI_TERMS = "(artificial intelligence OR machine learning OR generative AI OR LLM OR data scientist)"
WINDOW_DAYS = 31
SATURATION_TOPUP_N = 75


def search(key: str, query: str, n: int, start_date: str) -> tuple[float, list[dict]]:
    r = requests.post(
        "https://api.exa.ai/search",
        headers={"x-api-key": key, "Content-Type": "application/json"},
        json={
            "query": query,
            "type": "auto",
            "numResults": n,
            "startPublishedDate": start_date,
            "contents": {"highlights": {"numSentences": 3, "highlightsPerUrl": 2}},
        },
        timeout=120,
    )
    r.raise_for_status()
    d = r.json()
    cost = (d.get("costDollars") or {}).get("total", 0) or 0
    results = [
        {
            "title": x.get("title"),
            "url": x.get("url"),
            "published_date": x.get("publishedDate"),
            "highlights": x.get("highlights") or [],
        }
        for x in d.get("results", [])
    ]
    return cost, results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, help="e.g. 2026-06")
    parser.add_argument("--budget-cap", type=float, default=15.50)
    parser.add_argument("--limit", type=int, default=None, help="first N companies (testing)")
    args = parser.parse_args()

    load_dotenv(dotenv_path=".env")
    key = os.environ["EXA_API_KEY"]

    uni = pd.read_parquet("data/processed/universe/universe.parquet")
    uni = uni[uni["ticker"].notna() & ~uni["share_class_dup"]].drop_duplicates("ticker")
    companies = uni[["name", "ticker"]].sort_values("ticker").reset_index(drop=True)
    if args.limit:
        companies = companies.head(args.limit)

    out_dir = Path(f"data/raw/exa/{args.snapshot}")
    out_dir.mkdir(parents=True, exist_ok=True)
    start_date = (
        dt.datetime.now(_UTC) - dt.timedelta(days=WINDOW_DAYS)
    ).strftime("%Y-%m-%dT00:00:00.000Z")

    total_cost = 0.0
    n_done = n_skipped = n_topped = 0
    for _, row in companies.iterrows():
        path = out_dir / f"jobs_{row.ticker.replace('.', '-')}.json"
        if path.exists():
            n_skipped += 1
            continue
        if total_cost >= args.budget_cap:
            print(f"BUDGET CAP ${args.budget_cap} reached — stopping. done={n_done}")
            break
        query = f"{row['name']} job posting {AI_TERMS}"
        try:
            # No saturation top-up: neural search pads to the requested count
            # regardless of true posting volume (verified on the first 5
            # companies — all "saturated"), so deeper pulls buy padding, not
            # signal. Uniform depth also keeps cross-company counts comparable.
            cost, results = search(key, query, 25, start_date)
            total_cost += cost
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL {row.ticker}: {e}")
            time.sleep(1.0)
            continue
        path.write_text(
            json.dumps(
                {
                    "ticker": row.ticker,
                    "company": row["name"],
                    "snapshot": args.snapshot,
                    "query": query,
                    "window_start": start_date,
                    "fetched_at": dt.datetime.now(_UTC).isoformat(),
                    "n_results": len(results),
                    "results": results,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        n_done += 1
        if n_done % 50 == 0:
            print(f"  {n_done} done, cumulative ${total_cost:.2f}")
        time.sleep(0.25)

    manifest = {
        "snapshot": args.snapshot,
        "window_start": start_date,
        "companies_total": len(companies),
        "collected": n_done,
        "skipped_existing": n_skipped,
        "saturation_topups": n_topped,
        "exa_cost_dollars": round(total_cost, 3),
        "finished_at": dt.datetime.now(_UTC).isoformat(),
    }
    (out_dir / "_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
